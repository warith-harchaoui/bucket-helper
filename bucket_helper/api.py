"""
Bucket Helper — FastAPI HTTP surface.

Exposes every public function in :mod:`bucket_helper.main` as an HTTP
endpoint so ``bucket-helper`` can be dropped behind any reverse proxy
and consumed by other services. Kept intentionally minimal:

- Multipart uploads for the ``/upload`` endpoint (``UploadFile``),
  streamed straight to a temporary file so large blobs don't blow up
  memory.
- ``FileResponse`` for ``/download`` — bytes stream straight from S3 to
  the client with cleanup after the response is fully sent.
- JSON responses for the CRUD reads (``/exists``, ``/list``, ``/tempfile``,
  ``/strip-path``).
- ``BackgroundTasks`` cleans temp files after the response has been
  streamed — no leftover garbage on disk after a request.

Credentials flow
----------------
Two ways to feed credentials to the API:

- **Server-side default**: set ``BUCKET_HELPER_CONFIG`` in the process
  env; every request loads the same credentials via
  :func:`bucket_helper.credentials` (path or folder).
- **Per-request**: send ``s3_access_key`` / ``s3_secret_key`` /
  ``s3_bucket`` / ``s3_https`` (+ optional ``s3_endpoint_url``,
  ``s3_region``, ``s3_prefix``, ``s3_use_path_style``, ``s3_verify_ssl``)
  as form fields. Per-request wins over server default.

Install the extra to get the runtime dependencies::

    pip install 'bucket-helper[api]'

Then run the app with any ASGI server::

    uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000

Usage Example
-------------
>>> # Start the server:
>>> #   uvicorn bucket_helper.api:app --reload
>>> # Probe existence (server-side default cred loaded from BUCKET_HELPER_CONFIG):
>>> #   curl -F 'key=folder/obj.txt' http://localhost:8000/exists
>>> # Upload a file (per-request cred inline, path-style MinIO):
>>> #   curl -F 'file=@in.bin' -F 'key=folder/obj.bin' \\
>>> #        -F 's3_access_key=minioadmin' -F 's3_secret_key=minioadmin' \\
>>> #        -F 's3_bucket=uploads' -F 's3_https=http://minio.example.com:9000/uploads' \\
>>> #        -F 's3_endpoint_url=http://minio.example.com:9000' \\
>>> #        -F 's3_use_path_style=true' \\
>>> #        http://localhost:8000/upload
>>> # Full OpenAPI docs at http://localhost:8000/docs

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import os
import shutil
import tempfile
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

import botocore.exceptions

try:
    from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
    from fastapi.responses import FileResponse, JSONResponse
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The FastAPI HTTP surface requires the [api] extra. "
        "Install with: pip install 'bucket-helper[api]'"
    ) from exc

from . import (
    credentials,
    delete,
    download,
    exists,
    list_prefix,
    make_bucket,
    remote_tempfile,
    strip_s3_path,
    upload,
)

# ---------------------------------------------------------------------------
# App factory + shared plumbing
# ---------------------------------------------------------------------------


# Resolve the OpenAPI ``version`` from the installed package metadata so it
# tracks ``pyproject.toml`` automatically and never drifts to a stale literal.
# ``PackageNotFoundError`` covers the "running from a source tree with no
# installed dist" case; a broad fallback keeps app import robust even if metadata
# resolution misbehaves in some packaging edge case — a missing version string
# must never stop the API from booting.
try:
    _API_VERSION = _pkg_version("bucket-helper")
except PackageNotFoundError:  # pragma: no cover — source-tree / uninstalled run
    _API_VERSION = "0"
except Exception:  # pragma: no cover — never fatal on any packaging quirk
    _API_VERSION = "0"


app = FastAPI(
    title="Bucket Helper API",
    description=(
        "HTTP surface for the bucket-helper utilities: upload, download, "
        "delete, exists, list, make-bucket, tempfile, strip-path. Works "
        "against AWS S3 and any S3-compatible endpoint (MinIO, R2, B2, "
        "Spaces, Wasabi)."
    ),
    version=_API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(ValueError)
async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map a library ``ValueError`` (e.g. a malformed ``s3://`` URI) to 400.

    Without this, FastAPI's default handler turns it into a generic 500,
    indistinguishable from an actual server bug — this is ordinary
    client-input validation, not a server failure.
    """
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(botocore.exceptions.ClientError)
async def _client_error_handler(
    request: Request, exc: botocore.exceptions.ClientError
) -> JSONResponse:
    """Map an S3-side failure (auth, missing bucket, throttling, ...) to 502.

    The server did its job correctly; the *upstream* S3/S3-compatible
    endpoint is what failed — 502 (Bad Gateway) says that, 500 does not.
    """
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
async def _runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Map the library's own ``RuntimeError`` (``delete()``'s failure path,
    which already wraps a ``ClientError`` with context) to 502, same
    reasoning as :func:`_client_error_handler`.
    """
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# The set of credential keys the API accepts as form fields. Kept in
# one place so every endpoint that mutates S3 uses the same schema.
_CRED_FIELDS = (
    "s3_access_key",
    "s3_secret_key",
    "s3_bucket",
    "s3_https",
    "s3_region",
    "s3_endpoint_url",
    "s3_prefix",
    "s3_use_path_style",
    "s3_verify_ssl",
)


def _resolve_cred(overrides: dict) -> dict:
    """
    Build the credentials dict for a single request.

    Merging order (lowest → highest priority): server-side default
    (loaded from ``BUCKET_HELPER_CONFIG``), then per-request form fields.
    Empty / None values from the request do not override the server
    defaults — so the client can send a partial override.

    Parameters
    ----------
    overrides : dict
        Per-request credential fields (form data).

    Returns
    -------
    dict
        Merged credentials dict, ready for the library.
    """
    # Start from the server-side default if configured.
    base = {}
    default_config = os.environ.get("BUCKET_HELPER_CONFIG")
    if default_config:
        try:
            base = dict(credentials(default_config))
        except Exception as exc:  # pragma: no cover — surface as 500
            raise HTTPException(
                status_code=500,
                detail=f"Server default credentials failed to load: {exc}",
            ) from exc

    # Layer per-request overrides on top, skipping empty values so the
    # client can send partial overrides without wiping defaults.
    for k in _CRED_FIELDS:
        v = overrides.get(k)
        if v is not None and v != "":
            base[k] = v

    # Minimal sanity check — the library will re-check at call time but
    # a fast fail here gives a nicer 400.
    for required in ("s3_access_key", "s3_secret_key", "s3_bucket", "s3_https"):
        if required not in base:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Missing credential '{required}'. Either set "
                    "BUCKET_HELPER_CONFIG server-side or send the field with the request."
                ),
            )
    return base


def _spool(upload_file: UploadFile, dest_dir: Path) -> Path:
    """
    Persist an ``UploadFile`` to a temp path on disk.

    We copy the stream instead of holding the bytes in memory so a
    multi-hundred-MB blob does not OOM the worker. The file inherits
    the caller's suffix when available so downstream tooling picks
    the right content type.
    """
    ext = Path(upload_file.filename or "").suffix or ".bin"
    out = dest_dir / f"upload{ext}"
    with out.open("wb") as fp:
        shutil.copyfileobj(upload_file.file, fp)
    return out


def _cleanup(*paths) -> None:
    """Best-effort cleanup — never let a tidy-up failure kill a response."""
    for p in paths:
        try:
            path = Path(p)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)
        except Exception:
            pass


def _new_tmpdir() -> Path:
    """Create a request-scoped temp directory under the system temp root."""
    return Path(tempfile.mkdtemp(prefix="bucket-helper-"))


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Simple liveness probe — no dependency check, just proves the app is up."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Mutations — upload / delete / make-bucket
# ---------------------------------------------------------------------------


@app.post("/upload", tags=["actions"])
def upload_endpoint(
    background: BackgroundTasks,
    file: UploadFile = File(..., description="File to upload."),
    key: str | None = Form(
        None, description="Destination key or 's3://bucket/key' URI (empty = auto)."
    ),
    content_type: str | None = Form(None, description="Override the S3 Content-Type header."),
    # Per-request credentials (all optional — falls back to server default).
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """Upload a local file to S3. Returns the resulting ``s3://bucket/key`` URI."""
    # Merge server-default + per-request credentials once, up front.
    cred = _resolve_cred(locals())
    # Spool the multipart body to a temp dir first: boto3 wants a real path
    # on disk, and streaming avoids holding a large blob in memory.
    tmp = _new_tmpdir()
    try:
        src = _spool(file, tmp)
        uri = upload(
            local_path=str(src), cred=cred, s3_address=key or "", content_type=content_type
        )
    finally:
        # Small response, no need to defer cleanup — wipe the temp dir now.
        _cleanup(tmp)
    return JSONResponse({"s3_address": uri})


@app.post("/delete", tags=["actions"])
def delete_endpoint(
    key: str = Form(..., description="'s3://bucket/key' URI or bare key."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """Delete an S3 object (idempotent)."""
    # Resolve credentials, then dispatch straight to the library — S3's
    # delete is idempotent, so no "not found" special-casing is needed.
    cred = _resolve_cred(locals())
    delete(s3_address=key, cred=cred)
    return JSONResponse({"deleted": key})


@app.post("/make-bucket", tags=["actions"])
def make_bucket_endpoint(
    bucket: str = Form(..., description="Bucket name to create."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """Create a bucket. No-op if it already belongs to the caller."""
    # We always report ``created: True`` even on the idempotent no-op path:
    # the library treats "already owned by you" as success, so from the
    # caller's point of view the bucket now exists either way.
    cred = _resolve_cred(locals())
    make_bucket(bucket=bucket, cred=cred)
    return JSONResponse({"bucket": bucket, "created": True})


# ---------------------------------------------------------------------------
# Reads — exists / list / download / tempfile / strip-path
# ---------------------------------------------------------------------------


@app.post("/exists", tags=["reads"])
def exists_endpoint(
    key: str = Form(..., description="'s3://bucket/key' URI or bare key."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """Return ``{"exists": true|false}`` for the given key."""
    # Pure read: resolve creds, probe existence, hand back a JSON bool.
    cred = _resolve_cred(locals())
    return JSONResponse({"exists": exists(s3_address=key, cred=cred)})


@app.post("/list", tags=["reads"])
def list_endpoint(
    prefix: str = Form(..., description="Key prefix in the default bucket (may be empty)."),
    max_keys: int = Form(1000, description="Cap on the number of returned keys."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """List keys under ``prefix`` in the default bucket."""
    # Resolve creds, page through the prefix, and return the keys plus a
    # convenience count so clients don't have to len() the list themselves.
    cred = _resolve_cred(locals())
    keys = list_prefix(prefix=prefix, cred=cred, max_keys=max_keys)
    return JSONResponse({"keys": keys, "count": len(keys)})


@app.post("/download", tags=["reads"])
def download_endpoint(
    background: BackgroundTasks,
    key: str = Form(..., description="'s3://bucket/key' URI or bare key."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
):
    """Download an S3 object; the file is streamed back and cleaned up after."""
    # Stage the object on disk first, then let FileResponse stream it out.
    cred = _resolve_cred(locals())
    tmp = _new_tmpdir()
    # Preserve the suffix — clients that stream the response benefit.
    ext = Path(key).suffix or ".bin"
    dst = tmp / f"download{ext}"
    try:
        download(s3_address=key, local_path=str(dst), cred=cred)
    except Exception:
        # download() never wrote a usable file (missing key, S3 error, ...) —
        # nothing left to stream, so reclaim the temp dir immediately instead
        # of leaking it: the deferred background cleanup below is never
        # reached once this re-raises.
        _cleanup(tmp)
        raise
    # Defer cleanup to a background task: the file must still exist while
    # FileResponse streams it, so we can only wipe it once the response is sent.
    background.add_task(_cleanup, tmp)
    return FileResponse(
        str(dst),
        filename=Path(key).name or dst.name,
        media_type="application/octet-stream",
    )


@app.post("/tempfile", tags=["reads"])
def tempfile_endpoint(
    ext: str | None = Form(None, description="Extension for the generated name."),
    prefix: str | None = Form(None, description="Extra prefix under the default bucket."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """
    Return ``{"s3_address": ..., "public_url": ...}`` for a fresh random key.

    Does NOT upload anything. Since :func:`remote_tempfile` deletes the
    key on exit and we never wrote anything to it, this is a pure name
    generator — handy when the client wants to know *where* it will
    write before doing the upload itself.
    """
    cred = _resolve_cred(locals())
    # Enter and immediately leave the context manager: we only want the
    # generated (address, url) pair. Nothing is uploaded, so the auto-delete
    # on exit is a harmless no-op against a key that was never written.
    with remote_tempfile(cred, ext=ext or "", prefix=prefix or "") as (addr, url):
        payload = {"s3_address": addr, "public_url": url}
    return JSONResponse(payload)


@app.post("/strip-path", tags=["reads"])
def strip_path_endpoint(
    address: str = Form(..., description="Full 's3://bucket/key' URI or bare key."),
    s3_access_key: str | None = Form(None),
    s3_secret_key: str | None = Form(None),
    s3_bucket: str | None = Form(None),
    s3_https: str | None = Form(None),
    s3_region: str | None = Form(None),
    s3_endpoint_url: str | None = Form(None),
    s3_prefix: str | None = Form(None),
    s3_use_path_style: str | None = Form(None),
    s3_verify_ssl: str | None = Form(None),
) -> JSONResponse:
    """Return the key part of an ``s3://bucket/key`` address."""
    cred = _resolve_cred(locals())
    return JSONResponse({"key": strip_s3_path(address, cred)})
