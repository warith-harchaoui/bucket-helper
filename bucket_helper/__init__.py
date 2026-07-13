"""
Bucket Helper

Utility functions for AWS S3 and any S3-compatible object storage
(MinIO, Backblaze B2 S3 API, DigitalOcean Spaces, Cloudflare R2,
Wasabi, …) via :mod:`boto3`. Same shape as ``sftp-helper``:
``credentials()`` loader + ``upload`` / ``download`` / ``delete`` /
``exists`` / ``list_prefix`` / ``make_bucket`` + a ``remote_tempfile``
context manager for stage-and-share flows.

Also exposes multi-surface entry points:

- Library (this module) — the pure functions.
- argparse CLI — :mod:`bucket_helper.cli_argparse` (``bucket-helper``).
- click CLI     — :mod:`bucket_helper.cli_click` (``bucket-helper-click``).
- FastAPI HTTP  — :mod:`bucket_helper.api` (``uvicorn bucket_helper.api:app``).
- MCP tools     — :mod:`bucket_helper.mcp` (``bucket-helper-mcp``).

Usage Example
-------------
>>> import bucket_helper as bh
>>> cred = bh.credentials("path/to/s3_config.json")
>>> uri = bh.upload("local.txt", cred, "folder/uploaded.txt")
>>> assert bh.exists(uri, cred)
>>> bh.download(uri, "back.txt", cred)
>>> bh.delete(uri, cred)

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

__author__ = "Warith Harchaoui, Ph.D."
__email__ = "warithmetics@deraison.ai"

__all__ = [
    "credentials",
    "get_client_s3",
    "upload",
    "download",
    "delete",
    "exists",
    "list_prefix",
    "make_bucket",
    "remote_tempfile",
    "strip_s3_path",
]

from .main import (
    credentials,
    delete,
    download,
    exists,
    get_client_s3,
    list_prefix,
    make_bucket,
    remote_tempfile,
    strip_s3_path,
    upload,
)
