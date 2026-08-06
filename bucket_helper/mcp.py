"""Bucket Helper: Model Context Protocol (MCP) surface.

A thin adapter that exposes the FastAPI app from :mod:`bucket_helper.api` as
MCP tools, so any MCP-aware host (an agent runtime, an IDE integration, a
custom shell) can call the bucket-helper utilities — upload, download,
delete, exists, list, make-bucket, tempfile, strip-path — as first-class
tools, against AWS S3 or any S3-compatible endpoint (MinIO, R2, B2, Spaces,
Wasabi). Uses `fastapi-mcp` (https://github.com/tadata-org/fastapi_mcp): one
wrapper publishes the whole existing HTTP surface, so the routes are never
duplicated.

Install the extra to pull in ``fastapi-mcp``::

    pip install "bucket-helper[mcp]"

Then run the server (HTTP API + MCP endpoint at ``/mcp``)::

    bucket-helper-mcp                 # console entry point
    python -m bucket_helper.mcp       # equivalent

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

try:
    from fastapi_mcp import FastApiMCP
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        'The MCP surface needs the [mcp] extra: pip install "bucket-helper[mcp]"'
    ) from exc

# Reuse the exact same FastAPI app: MCP is a thin wrapper on top, no new routes.
from bucket_helper.api import app

# Publish the HTTP endpoints (upload / download / delete / exists / list /
# make-bucket / tempfile / strip-path) as MCP tools.
mcp = FastApiMCP(
    app,
    name="bucket-helper",
    description=(
        "Bucket Helper MCP tools: upload, download, delete, exists, list, "
        "make-bucket, tempfile, strip-path against AWS S3 or any "
        "S3-compatible object storage (MinIO, R2, B2, Spaces, Wasabi). "
        "Credentials come from BUCKET_HELPER_CONFIG server-side or per call."
    ),
)
# Newer fastapi-mcp splits mount() into transport-specific mount_http(); fall back to
# the legacy mount() so a range of fastapi-mcp versions keeps working.
if hasattr(mcp, "mount_http"):
    mcp.mount_http()
else:  # pragma: no cover - legacy fastapi-mcp
    mcp.mount()


def main() -> None:
    """Console entry point (``bucket-helper-mcp``): serve the API + MCP endpoint.

    Boots the FastAPI app (now serving both the ``/upload``/``/download``/...
    routes and the ``/mcp`` MCP endpoint) with uvicorn in a single worker.
    Local-first by default: binds to loopback (override with
    ``BUCKET_HELPER_HOST`` / ``BUCKET_HELPER_PORT``).
    """
    import os

    import uvicorn

    host = os.environ.get("BUCKET_HELPER_HOST", "127.0.0.1")
    port = int(os.environ.get("BUCKET_HELPER_PORT", "8000"))
    print(f"Bucket Helper API + MCP -> http://{host}:{port}  (MCP at /mcp)")
    uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":  # pragma: no cover
    main()
