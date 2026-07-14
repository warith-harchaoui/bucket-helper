"""
Bucket Helper — Model Context Protocol (MCP) surface.

Adapter that exposes the FastAPI app defined in :mod:`bucket_helper.api`
as MCP tools so an MCP-aware client (Claude Desktop, custom agents, IDE
integrations, …) can call ``upload`` / ``download`` / ``exists`` /
``list`` / ``delete`` / ``make-bucket`` / ``tempfile`` / ``strip-path``
as first-class tools. Uses :mod:`fastapi_mcp`
(https://github.com/tadata-org/fastapi_mcp) — one line wraps the whole
existing HTTP surface, so we never duplicate the route definitions.

Install the extras to pull in ``fastapi-mcp``::

    pip install 'bucket-helper[api,mcp]'

Then run the MCP server::

    bucket-helper-mcp                 # entry point (see pyproject)
    # or, equivalently:
    python -m bucket_helper.mcp

Usage Example
-------------
>>> # Register the MCP endpoint in your client. It publishes:
>>> #   upload / download / delete / exists / list /
>>> #   make-bucket / tempfile / strip-path
>>> # …with the same argument names as the FastAPI routes.

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

try:
    from fastapi_mcp import FastApiMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The MCP surface requires the [mcp] extra. "
        "Install with: pip install 'bucket-helper[api,mcp]'"
    ) from exc

# Reuse the exact same FastAPI app — MCP is a thin wrapper on top.
from .api import app

# ``FastApiMCP`` mounts an MCP endpoint on the existing FastAPI app; we
# store the wrapped instance at module scope so downstream code (tests,
# ASGI runners) can access both the FastAPI app and the MCP handler.
mcp = FastApiMCP(
    app,
    name="bucket-helper",
    description=(
        "Bucket Helper MCP tools: upload, download, delete, exists, list, "
        "make-bucket, tempfile, strip-path. Works against AWS S3 and any "
        "S3-compatible endpoint (MinIO, R2, B2, Spaces, Wasabi)."
    ),
)
# Attach the MCP endpoint to the FastAPI app. Newer fastapi-mcp releases
# split ``mount()`` into transport-specific ``mount_http()`` (recommended)
# and ``mount_sse()``. Fall back to the legacy ``mount()`` on older
# versions so users can install a range of ``fastapi-mcp`` versions.
if hasattr(mcp, "mount_http"):
    mcp.mount_http()
else:  # pragma: no cover — legacy fastapi-mcp
    mcp.mount()


def main() -> None:
    """
    Entry point for the ``bucket-helper-mcp`` console script.

    Boots the FastAPI app (which now serves both the ``/…`` HTTP routes
    and the MCP endpoint) with ``uvicorn`` in single-worker mode. Meant
    for local / container usage; behind a real load balancer use
    ``uvicorn``/``gunicorn`` directly.
    """
    import os

    import uvicorn

    host = os.environ.get("BUCKET_HELPER_HOST", "0.0.0.0")
    port = int(os.environ.get("BUCKET_HELPER_PORT", "8000"))
    # ``log_level`` is intentionally left at uvicorn's default so
    # operators can tune via env / cli. Single worker keeps in-flight
    # S3 connections predictable.
    uvicorn.run(app, host=host, port=port, workers=1)


if __name__ == "__main__":  # pragma: no cover
    main()
