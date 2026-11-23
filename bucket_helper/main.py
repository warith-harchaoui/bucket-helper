"""
Bucket Helper

Utility functions to interact with **AWS S3 and any S3-compatible
object storage**: upload, download, list, exists, remove, plus a
``remote_tempfile`` context manager that gives you a unique key and
cleans up automatically.

Backed by :mod:`boto3`. SSL certificate verification is on by default
and never disabled silently — callers may opt out per-call via
``cred["s3_verify_ssl"] = false`` only if they really mean it (handy
for a self-signed MinIO behind a corporate VPN).

S3-compatible endpoints
-----------------------
Anything that speaks the AWS S3 API works transparently — just set
``cred["s3_endpoint_url"]`` to the endpoint:

- **AWS S3** : leave ``s3_endpoint_url`` empty or unset (boto3 picks
  ``s3.<region>.amazonaws.com`` automatically).
- **MinIO** : ``"http://minio.example.com:9000"`` or ``"https://minio.example.com"``.
- **DigitalOcean Spaces** : ``"https://nyc3.digitaloceanspaces.com"``.
- **Cloudflare R2** : ``"https://<account_id>.r2.cloudflarestorage.com"``.
- **Backblaze B2** (S3 API) : ``"https://s3.us-west-001.backblazeb2.com"``.
- **Wasabi** : ``"https://s3.us-east-1.wasabisys.com"``.
- **Scaleway** (Paris, Amsterdam, Warsaw) : ``"https://s3.fr-par.scw.cloud"``,
  ``"https://s3.nl-ams.scw.cloud"``, ``"https://s3.pl-waw.scw.cloud"`` — or
  :func:`scaleway_endpoint`.

Usage Example
-------------
>>> import bucket_helper as bh
>>> cred = bh.credentials("path/to/settings.yaml")
>>> # Upload a local file at an explicit key.
>>> uri = bh.upload("local.bin", cred, "folder/local.bin")
>>> # Probe it, download it, list around it, then delete it.
>>> assert bh.exists(uri, cred)
>>> bh.download(uri, "back.bin", cred)
>>> [k for k in bh.list_prefix("folder/", cred)]  # noqa: E501
>>> bh.delete(uri, cred)

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import atexit
import contextlib
import hashlib
import logging
import os
import secrets
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

import boto3
import botocore.exceptions
import os_helper as osh

logger = logging.getLogger(__name__)

# Diagnostics go through os-helper's logging surface (``osh.info`` /
# ``osh.warning`` / ``osh.error``) rather than stdlib ``logging`` or bare
# ``print(...)``. This is the suite-wide convention: verbosity is controlled
# from one place across every AI-Helpers package, so callers tune it once.

# ---------------------------------------------------------------------------
# Credentials loader
# ---------------------------------------------------------------------------


def credentials(config_path: str | None = None) -> dict:
    """
    Retrieve S3 credentials from a configuration file, folder, or environment.

    Loads (in this precedence order) from JSON / YAML files, ``.env``, then
    environment variables — see :func:`os_helper.get_config`.

    Required keys
    -------------
    - ``s3_access_key`` : your access key ID
    - ``s3_secret_key`` : your secret access key
    - ``s3_bucket``     : default bucket name
    - ``s3_https``      : base public URL for built objects, e.g.
      ``"https://my-bucket.s3.eu-west-3.amazonaws.com"`` or
      ``"https://cdn.example.com"`` (used by ``remote_tempfile`` to build
      the public URL handed back to the caller)

    Optional keys
    -------------
    - ``s3_region``       : AWS region (defaults to ``"us-east-1"`` if absent,
      mostly irrelevant for path-style MinIO etc.)
    - ``s3_endpoint_url`` : custom endpoint for S3-compatible storage
      (MinIO, R2, B2, Spaces, Wasabi). Empty / missing → AWS S3.
    - ``s3_prefix``       : default key prefix (path-like, e.g. ``"uploads"``)
    - ``s3_use_path_style`` : ``"true"`` to force path-style addressing
      (typical for MinIO with custom domains). Default ``"false"`` (uses
      virtual-hosted style).
    - ``s3_verify_ssl``   : ``"false"`` to disable TLS verification (use
      sparingly — e.g. dev MinIO with self-signed cert).
    - ``s3_retry_mode``   : botocore retry mode, ``"standard"`` (default:
      exponential backoff with full jitter and a retry quota) or
      ``"adaptive"`` (also slows the send rate after throttling; AWS calls it
      experimental).

    Returns
    -------
    dict
        Credentials dict.
    """
    required = ["s3_access_key", "s3_secret_key", "s3_bucket", "s3_https"]
    cred = osh.get_config(required, "S3", config_path)
    # Pick up optional keys best-effort from the environment so the bucket /
    # MinIO endpoint can be configured the same way as the required keys
    # without having to reach into os.environ from the caller.
    for opt in (
        "s3_region",
        "s3_endpoint_url",
        "s3_prefix",
        "s3_use_path_style",
        "s3_verify_ssl",
        "s3_retry_mode",
    ):
        if opt in cred:
            continue
        env_val = os.environ.get(opt.upper()) or os.environ.get(opt)
        if env_val is not None:
            cred[opt] = env_val
    return cred


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def _truthy(value: object) -> bool:
    """Lenient bool parser for string-valued config flags."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Pacing — one client reused, jittered gaps, SDK retries with full jitter.
# ---------------------------------------------------------------------------
#
# Why this exists. Every call used to build a fresh client, so a loop of small
# calls (an existence check per key, a delete per key) opened a new TLS
# connection each time and fired requests back to back. Object stores throttle
# that (S3 answers 503 SlowDown; S3-compatible hosts publish lower limits or
# none), and a client that hammers a host until it is throttled is at fault,
# not the host. Applied here once so no caller has to remember it:
#
# 1. One client per credential set, reused for the life of the process: its
#    urllib3 pool keeps connections alive instead of a handshake per call, and
#    its retry quota is shared instead of reset on every call.
# 2. A random pause before every HTTP request, measured from the previous
#    one, paginator pages and multipart parts included (a ``before-send``
#    hook sees them all). Random, never fixed: fixed intervals line up across
#    processes (AWS Architecture Blog, "Exponential Backoff and Jitter").
# 3. Throttling and transient errors are retried by botocore's documented
#    "standard" mode: exponential backoff with full jitter plus a retry quota
#    that stops retry storms. ``s3_retry_mode: adaptive`` adds client-side
#    rate limiting that slows down after throttling; AWS calls that mode
#    experimental, so it is opt-in.
#
# Tunable without code: BUCKET_HELPER_PACE as "min,max" seconds ("0,0"
# disables, e.g. for a bulk job against your own MinIO).


def _env_range(name: str, default: tuple[float, float]) -> tuple[float, float]:
    """Read a ``"min,max"`` seconds range from the environment."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        low, high = (float(x) for x in raw.split(","))
    except ValueError:
        logger.warning(f"{name}={raw!r} is not 'min,max' seconds; using {default}")
        return default
    return (max(0.0, min(low, high)), max(0.0, low, high))


_PACE = _env_range("BUCKET_HELPER_PACE", (0.3, 1.5))
_RETRY_MODES = {"standard", "adaptive", "legacy"}
_pace_lock = threading.Lock()
_last_request: dict[str, float] = {}
_clients: dict[tuple, boto3.client] = {}
_clients_lock = threading.Lock()
_rng = secrets.SystemRandom()


def _wait_turn(host: str) -> None:
    """Sleep until a random gap has passed since the last request to ``host``."""
    low, high = _PACE
    with _pace_lock:
        last = _last_request.get(host)
        if last is not None and high > 0:
            remaining = last + _rng.uniform(low, high) - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
        _last_request[host] = time.monotonic()


def _pace_hook(request, **_kwargs) -> None:
    """botocore ``before-send`` handler: pace every HTTP request per host."""
    _wait_turn(urlparse(request.url).netloc)


def _client_key(cred: dict) -> tuple:
    """Everything that changes how a client talks to the store (never the secret itself)."""
    secret_digest = hashlib.sha256(str(cred["s3_secret_key"]).encode("utf-8")).hexdigest()
    return (
        str(cred["s3_access_key"]),
        secret_digest,
        cred.get("s3_endpoint_url") or "",
        cred.get("s3_region") or "us-east-1",
        _truthy(cred.get("s3_use_path_style")),
        "s3_verify_ssl" not in cred or _truthy(cred.get("s3_verify_ssl")),
        str(cred.get("s3_retry_mode") or "standard"),
    )


def _close_clients() -> None:
    """Close every cached client's connection pool (at exit, or between tests)."""
    with _clients_lock:
        for client in _clients.values():
            # Some boto3 versions raise on ``close()`` (a known quirk); a
            # failed tidy-up must never mask anything.
            with contextlib.suppress(Exception):  # pragma: no cover — boto3 quirk
                client.close()
        _clients.clear()


atexit.register(_close_clients)


def _build_client(cred: dict) -> boto3.client:
    """Build one boto3 S3 client honoring ``cred``, with the pacing hook attached."""
    endpoint_url = cred.get("s3_endpoint_url")
    if osh.emptystring(endpoint_url):
        endpoint_url = None

    region = cred.get("s3_region") or "us-east-1"

    use_path_style = _truthy(cred.get("s3_use_path_style"))
    addressing_style = "path" if use_path_style else "auto"

    verify_ssl = True
    if "s3_verify_ssl" in cred and not _truthy(cred.get("s3_verify_ssl")):
        verify_ssl = False

    retry_mode = str(cred.get("s3_retry_mode") or "standard").strip().lower()
    if retry_mode not in _RETRY_MODES:
        logger.warning(f"s3_retry_mode={retry_mode!r} unknown; using 'standard'")
        retry_mode = "standard"

    config = boto3.session.Config(
        signature_version="s3v4",
        s3={"addressing_style": addressing_style},
        retries={"max_attempts": 5, "mode": retry_mode},
    )

    client = boto3.client(
        "s3",
        aws_access_key_id=cred["s3_access_key"],
        aws_secret_access_key=cred["s3_secret_key"],
        region_name=region,
        endpoint_url=endpoint_url,
        verify=verify_ssl,
        config=config,
    )
    client.meta.events.register("before-send.s3", _pace_hook)
    return client


@contextmanager
def get_client_s3(cred: dict) -> Iterator[boto3.client]:
    """
    Yield the boto3 S3 client for ``cred``, built once and then reused.

    The client is configured per AWS S3 (no ``endpoint_url``) or per the
    S3-compatible endpoint when ``cred["s3_endpoint_url"]`` is set. It is
    cached per credential set for the life of the process (boto3 clients are
    thread-safe), so its connection pool and retry quota carry over from one
    call to the next, and every request it sends is paced (see above).

    Yields
    ------
    boto3.client
        Ready-to-use S3 client. Do not close it: it is shared.
    """
    key = _client_key(cred)
    with _clients_lock:
        client = _clients.get(key)
        if client is None:
            client = _clients[key] = _build_client(cred)
    yield client


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _split_s3_address(s3_address: str, default_bucket: str) -> tuple[str, str]:
    """Normalise ``s3_address`` into ``(bucket, key)``.

    Accepted forms:
    - ``"s3://bucket/path/to/object"`` → ``("bucket", "path/to/object")``
    - ``"path/to/object"`` (no scheme) → ``(default_bucket, "path/to/object")``
    """
    if s3_address.startswith("s3://"):
        parsed = urlparse(s3_address)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if not bucket or not key:
            raise ValueError(f"Malformed s3:// URI: {s3_address!r}")
        return bucket, key
    return default_bucket, s3_address.lstrip("/")


def _build_public_url(cred: dict, key: str) -> str:
    """Compose ``cred["s3_https"] + "/" + key`` cleanly."""
    base = cred["s3_https"].rstrip("/")
    return f"{base}/{key.lstrip('/')}"


def strip_s3_path(s3_address: str, cred: dict) -> str:
    """Return the key part of ``s3_address`` (compat with sftp-helper's
    ``strip_sftp_path``)."""
    _, key = _split_s3_address(s3_address, cred["s3_bucket"])
    return key


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def exists(s3_address: str, cred: dict) -> bool:
    """Return True if the object at ``s3_address`` exists, False otherwise."""
    bucket, key = _split_s3_address(s3_address, cred["s3_bucket"])
    with get_client_s3(cred) as s3:
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return True
        except botocore.exceptions.ClientError as err:
            code = err.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise


#: Scaleway Object Storage regions and their S3 endpoints.
SCALEWAY_REGIONS: tuple[str, ...] = ("fr-par", "nl-ams", "pl-waw")


def scaleway_endpoint(region: str = "fr-par") -> str:
    """The S3 endpoint of a Scaleway Object Storage region.

    Parameters
    ----------
    region : str, optional
        ``"fr-par"`` (Paris, default), ``"nl-ams"`` (Amsterdam) or ``"pl-waw"``
        (Warsaw).

    Returns
    -------
    str
        The endpoint URL, to put in ``cred["s3_endpoint_url"]`` with
        ``cred["s3_region"]`` set to the same region.

    Raises
    ------
    ValueError
        For a region Scaleway does not offer.

    Examples
    --------
    >>> scaleway_endpoint()
    'https://s3.fr-par.scw.cloud'
    >>> scaleway_endpoint("nl-ams")
    'https://s3.nl-ams.scw.cloud'
    """
    if region not in SCALEWAY_REGIONS:
        raise ValueError(
            f"Scaleway region {region!r} unknown; use one of {', '.join(SCALEWAY_REGIONS)}"
        )
    return f"https://s3.{region}.scw.cloud"


def upload(
    local_path: str,
    cred: dict,
    s3_address: str = "",
    content_type: str | None = None,
    *,
    if_absent: bool = False,
) -> str:
    """
    Upload a local file to S3.

    Parameters
    ----------
    local_path : str
        Path to the local file.
    cred : dict
        Credentials dict from :func:`credentials`.
    s3_address : str, optional
        Destination — either ``"s3://bucket/key"`` or a key under the
        default bucket. If empty, a random unique hex name is generated
        (not derived from the file's content) under ``cred["s3_prefix"]``
        (if set) of the default bucket.
    content_type : str, optional
        Override the MIME ``Content-Type`` header. If None, boto3 lets the
        server default (typically ``application/octet-stream``).
    if_absent : bool, optional
        Write only if no object holds that key yet; never overwrite. For
        content-addressed storage, where a key names exactly one content, and
        for two writers racing to the same key. The request carries
        ``If-None-Match: *`` (S3 conditional writes), so the server itself
        refuses the second write; the key is also checked first, so a provider
        that ignores the header still does not overwrite an object that was
        already there (the race window then remains, and is the provider's).

    Returns
    -------
    str
        The full ``s3://bucket/key`` URI of the uploaded object.

    Raises
    ------
    botocore.exceptions.ClientError
        If the upload fails (permissions, bucket missing, network).
    AssertionError
        If ``local_path`` does not exist or is empty.
    FileExistsError
        With ``if_absent=True``, when the key already holds an object.
    """
    osh.checkfile(local_path, msg=f"Local file not found / empty: {local_path}", check_empty=True)

    if osh.emptystring(s3_address):
        _, _, ext = osh.folder_name_ext(local_path)
        prefix = cred.get("s3_prefix")
        prefix = "" if osh.emptystring(prefix) else prefix.strip("/") + "/"
        name = secrets.token_hex(16)
        if not osh.emptystring(ext):
            name = f"{name}.{ext.lstrip('.')}"
        s3_address = f"{prefix}{name}"

    bucket, key = _split_s3_address(s3_address, cred["s3_bucket"])

    extra_args: dict = {}
    if content_type is not None:
        extra_args["ContentType"] = content_type

    # Stream with the shared suite progress bar (byte-scaled, auto-quiet on a
    # non-TTY). boto3 invokes the Callback with the byte delta per part, which is
    # exactly what ``tqdm.update`` expects — so ``bar.update`` wires in directly.
    if if_absent:
        uri = f"s3://{bucket}/{key}"
        if exists(uri, cred):
            raise FileExistsError(f"{uri} already exists; if_absent=True never overwrites")
        with get_client_s3(cred) as s3, open(local_path, "rb") as body:
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=body, IfNoneMatch="*", **extra_args)
            except botocore.exceptions.ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if code in ("PreconditionFailed", "ConditionalRequestConflict") or status in (
                    409,
                    412,
                ):
                    raise FileExistsError(f"{uri} was written by someone else first") from exc
                raise
        logger.info("S3 upload OK (if absent): %s → %s", local_path, uri)
        return uri

    size = osh.size_file(local_path)
    with get_client_s3(cred) as s3, osh.progress_bar(total=size, desc=key) as bar:
        s3.upload_file(local_path, bucket, key, ExtraArgs=extra_args or None, Callback=bar.update)

    uri = f"s3://{bucket}/{key}"
    logger.info("S3 upload OK: %s → %s", local_path, uri)
    return uri


def download(s3_address: str, local_path: str, cred: dict) -> str:
    """
    Download an S3 object to a local path. Returns ``local_path`` on success.
    """
    bucket, key = _split_s3_address(s3_address, cred["s3_bucket"])

    parent = os.path.dirname(local_path)
    if parent:
        osh.make_directory(parent)

    with get_client_s3(cred) as s3:
        # Cheap metadata call for the bar's total; fall back to an open-ended bar
        # if HEAD is denied. boto3's Callback delta feeds ``tqdm.update`` directly.
        try:
            size = s3.head_object(Bucket=bucket, Key=key).get("ContentLength")
        except botocore.exceptions.ClientError:
            size = None
        with osh.progress_bar(total=size, desc=key) as bar:
            s3.download_file(bucket, key, local_path, Callback=bar.update)

    osh.checkfile(
        local_path, msg=f"Download failed (file missing or empty): {local_path}", check_empty=True
    )
    logger.info("S3 download OK: s3://%s/%s → %s", bucket, key, local_path)
    return local_path


def delete(s3_address: str, cred: dict) -> bool:
    """
    Delete an S3 object. Returns True if the object is gone after the call
    (including the case where it never existed — S3's delete is idempotent).
    """
    bucket, key = _split_s3_address(s3_address, cred["s3_bucket"])
    with get_client_s3(cred) as s3:
        try:
            s3.delete_object(Bucket=bucket, Key=key)
        except botocore.exceptions.ClientError as err:
            raise RuntimeError(f"Failed to delete S3 object s3://{bucket}/{key}: {err}") from err
    logger.info("S3 delete OK: s3://%s/%s", bucket, key)
    return True


def list_prefix(prefix: str, cred: dict, *, max_keys: int = 1000) -> list[str]:
    """
    List the object keys under ``prefix`` in the default bucket.

    Returns at most ``max_keys`` keys, ordered by S3's lexicographic
    response (no client-side sort). For very large prefixes, paginate
    via boto3 directly with ``get_client_s3``.
    """
    bucket = cred["s3_bucket"]
    keys: list[str] = []
    with get_client_s3(cred) as s3:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=bucket,
            Prefix=prefix.lstrip("/"),
            PaginationConfig={"MaxItems": max_keys},
        ):
            for obj in page.get("Contents") or []:
                keys.append(obj["Key"])
                if len(keys) >= max_keys:
                    return keys
    return keys


def list_prefix_page(prefix: str, cred: dict, *, max_keys: int = 1000) -> tuple[list[str], bool]:
    """List keys under ``prefix``, and say whether more were left behind.

    :func:`list_prefix` returns at most ``max_keys`` keys and cannot tell the
    caller whether that was all of them. For a human reading a terminal that is
    a mild annoyance; for a program it is a correctness problem, because a
    response of 1000 keys looks identical whether the prefix holds exactly 1000
    objects or fifty thousand.

    This asks S3 for one key more than it will return. If that extra key
    arrives, there is more behind it. The cost is a single additional key, and
    it turns an ambiguous answer into a definite one.

    Parameters
    ----------
    prefix : str
        Key prefix to list under, in the credentials' default bucket.
    cred : dict
        Credentials, as accepted by :func:`get_client_s3`.
    max_keys : int, default 1000
        Maximum number of keys to return.

    Returns
    -------
    tuple[list[str], bool]
        The keys (at most ``max_keys`` of them), and ``True`` when S3 held
        more than that under the prefix.

    Examples
    --------
    >>> keys, truncated = list_prefix_page("logs/", cred, max_keys=10)  # doctest: +SKIP
    >>> if truncated:  # doctest: +SKIP
    ...     print("there are more than 10 objects under logs/")
    """
    # One extra key is the whole trick: present ⇒ truncated.
    probed = list_prefix(prefix, cred, max_keys=max_keys + 1)
    if len(probed) > max_keys:
        return probed[:max_keys], True
    return probed, False


def make_bucket(bucket: str, cred: dict) -> None:
    """Create a bucket if it doesn't exist.

    Honors ``cred["s3_region"]`` for the LocationConstraint. No-op when
    the bucket already exists and is owned by the credentials.
    """
    region = cred.get("s3_region") or "us-east-1"
    with get_client_s3(cred) as s3:
        try:
            if region == "us-east-1":
                # us-east-1 must NOT have a LocationConstraint — AWS quirk.
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            logger.info("S3 bucket created: %s (region=%s)", bucket, region)
        except botocore.exceptions.ClientError as err:
            code = err.response.get("Error", {}).get("Code", "")
            if code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                logger.info("S3 bucket already exists: %s", bucket)
                return
            raise


# ---------------------------------------------------------------------------
# remote_tempfile — unique key, auto-cleanup
# ---------------------------------------------------------------------------


@contextmanager
def remote_tempfile(
    cred: dict,
    *,
    ext: str = "",
    prefix: str = "",
) -> Iterator[tuple[str, str]]:
    """
    Yield ``(s3_address, public_url)`` for a unique key, deleted on exit.

    Useful for stage-and-share flows: upload a generated file, hand the
    public URL to whoever needs it (a downstream worker, a webhook
    target, a test fixture), and let the context manager clean up the
    remote artifact at the end of the block — even on exception.

    Parameters
    ----------
    cred : dict
        Credentials dict from :func:`credentials`. The object goes under
        ``cred["s3_bucket"]``; the public URL is built from
        ``cred["s3_https"]``.
    ext : str, optional
        Extension to append to the random name (with or without leading
        ``.``). Default empty.
    prefix : str, optional
        Extra path segment under the bucket / default prefix. Default empty.

    Yields
    ------
    (s3_address, public_url) : tuple of str
        ``s3_address`` is ``"s3://bucket/key"``; ``public_url`` is the
        ``https://...`` URL built from ``cred["s3_https"]``.

    Example
    -------
    >>> import bucket_helper as bh
    >>> cred = bh.credentials("path/to/settings.yaml")
    >>> with bh.remote_tempfile(cred, ext="json") as (addr, url):
    ...     bh.upload("payload.json", cred, addr, content_type="application/json")
    ...     # publish `url` somewhere, e.g. trigger a webhook
    >>> # the object is gone after the block — even if the body raised.
    """
    name = secrets.token_hex(16)
    if not osh.emptystring(ext):
        name = f"{name}.{ext.lstrip('.')}"

    base_prefix = cred.get("s3_prefix")
    base_prefix = "" if osh.emptystring(base_prefix) else base_prefix.strip("/")
    if not osh.emptystring(prefix):
        clean = prefix.strip("/")
        base_prefix = f"{base_prefix}/{clean}" if base_prefix else clean

    key = f"{base_prefix}/{name}" if base_prefix else name
    bucket = cred["s3_bucket"]
    s3_address = f"s3://{bucket}/{key}"
    public_url = _build_public_url(cred, key)

    try:
        yield s3_address, public_url
    finally:
        # Best-effort cleanup; never re-raise so the caller's original
        # exception (if any) wins.
        try:
            delete(s3_address, cred)
        except Exception as err:  # pragma: no cover
            logger.warning("S3 remote_tempfile cleanup failed for %s: %s", s3_address, err)
