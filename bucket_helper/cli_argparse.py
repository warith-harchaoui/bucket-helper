"""
Bucket Helper — argparse-based command-line interface.

Thin wrapper around the pure functions in :mod:`bucket_helper.main` that
exposes the whole toolkit as subcommands under a single ``bucket-helper``
entry point. Written with :mod:`argparse` from the standard library so
the CLI works out of the box on any Python install that has the package
installed — no extra dependency required.

Every subcommand reads credentials from ``--config`` (path to a JSON /
YAML file, or a folder holding one, or empty for env-only). Under the
hood we call :func:`bucket_helper.credentials`, so the same precedence
order (JSON → YAML → ``.env`` → environment) applies here as in the
library.

Subcommands
-----------
- ``upload``     — send a local file to S3 (auto-key if omitted)
- ``download``   — fetch an S3 object to a local path
- ``delete``     — delete an S3 object (idempotent)
- ``exists``     — probe whether an S3 object exists (exit code 0/1)
- ``list``       — list keys under a prefix in the default bucket
- ``make-bucket``— create a bucket (no-op if it already exists)
- ``tempfile``   — generate a unique random key + public URL (no upload)
- ``strip-path`` — normalise ``s3://bucket/key`` into the key part

Usage Example
-------------
>>> #   bucket-helper upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
>>> #   bucket-helper download    --config settings.yaml --key folder/uploaded.txt --output local.txt
>>> #   bucket-helper delete      --config settings.yaml --key folder/uploaded.txt
>>> #   bucket-helper exists      --config settings.yaml --key folder/uploaded.txt
>>> #   bucket-helper list        --config settings.yaml --prefix folder/
>>> #   bucket-helper make-bucket --config settings.yaml --bucket new-bucket
>>> #   bucket-helper tempfile    --config settings.yaml --ext json --prefix runs
>>> #   bucket-helper strip-path  --config settings.yaml --address s3://my-bucket/path/to/obj

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

# Import the pure functions once here — every subcommand is a thin dispatch
# on top of these, no logic duplication.
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
# Credential loading helper
#
# Every subcommand takes ``--config`` — the path (or folder) passed to
# :func:`bucket_helper.credentials`. Isolating the load call here means
# subcommands do not repeat the plumbing and any future change to the
# credential contract lives in one place.
# ---------------------------------------------------------------------------


def _load_cred(ns: argparse.Namespace) -> dict:
    """Load the credentials dict for a parsed CLI invocation.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed arguments; only ``ns.config`` is read here.

    Returns
    -------
    dict
        Credentials from :func:`bucket_helper.credentials`.
    """
    # ``config`` is optional. If missing we let :func:`credentials` fall
    # back to environment variables / .env — that is how the library
    # itself behaves.
    return credentials(ns.config)


# ---------------------------------------------------------------------------
# Result output helper
#
# CLI *result* output (a URI, a listing, a JSON blob, "true"/"false") must go
# to stdout so shell pipelines can consume it: `bucket-helper upload ... | ...`.
# That is deliberately NOT a logging surface — logging goes to stderr and is
# level-gated, which would silently drop the CLI's actual result. We route it
# through this one explicit ``sys.stdout`` writer instead of scattering bare
# ``print(...)`` calls, so the "result → stdout" contract lives in one place
# and stays greppable / testable.
# ---------------------------------------------------------------------------


def _emit(text: str) -> None:
    """Write one line of CLI *result* output to stdout.

    Parameters
    ----------
    text : str
        The machine-consumable result to print (URI, key, JSON, boolean
        word, ...). A trailing newline is appended so downstream pipeline
        stages (``xargs``, ``read``, ...) see one record per line.

    Notes
    -----
    Result output goes to ``sys.stdout`` on purpose, not to :mod:`logging`:
    logging targets stderr and is level-gated, so using it here would break
    the documented "chain the result on stdout" contract of every subcommand.
    """
    # Single, centralized stdout write — the CLI's public output channel.
    sys.stdout.write(f"{text}\n")


# ---------------------------------------------------------------------------
# Subcommand handlers
#
# Each handler receives the parsed ``argparse.Namespace`` and returns a
# process exit code (``0`` on success). Handlers deliberately stay short:
# they translate CLI arguments into keyword arguments for the underlying
# library function, emit a machine-friendly result (JSON for structured
# outputs, plain path for single-file outputs), and let exceptions
# propagate as non-zero exit codes.
# ---------------------------------------------------------------------------


def _handle_upload(ns: argparse.Namespace) -> int:
    """Handle ``upload``: send a local file and print its ``s3://`` URI.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``input`` / ``key`` / ``content_type``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # upload() returns the s3:// URI of the uploaded object.
    cred = _load_cred(ns)
    uri = upload(
        local_path=ns.input,
        cred=cred,
        s3_address=ns.key or "",
        content_type=ns.content_type,
    )
    # Emit the s3:// URI so shell pipelines can chain on stdout.
    _emit(uri)
    return 0


def _handle_download(ns: argparse.Namespace) -> int:
    """Handle ``download``: fetch an object and print the local path.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``key`` / ``output``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # download() returns the local_path on success.
    cred = _load_cred(ns)
    out = download(s3_address=ns.key, local_path=ns.output, cred=cred)
    _emit(out)
    return 0


def _handle_delete(ns: argparse.Namespace) -> int:
    """Handle ``delete``: remove an object (idempotent).

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``key``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # delete() is idempotent and always returns True on success.
    cred = _load_cred(ns)
    delete(s3_address=ns.key, cred=cred)
    return 0


def _handle_exists(ns: argparse.Namespace) -> int:
    """Handle ``exists``: print ``true``/``false`` and mirror it in the exit code.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``key``).

    Returns
    -------
    int
        ``0`` if the object exists, ``1`` otherwise — so shell ``if`` works.
    """
    # exists() returns a bool — map to process exit code 0/1 so shell
    # `if bucket-helper exists ...; then ...; fi` works naturally.
    cred = _load_cred(ns)
    present = exists(s3_address=ns.key, cred=cred)
    _emit("true" if present else "false")
    return 0 if present else 1


def _handle_list(ns: argparse.Namespace) -> int:
    """Handle ``list``: print each key under a prefix, one per line.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``prefix`` / ``max_keys``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # list_prefix() returns a list of keys — emit them one per line so
    # shell pipelines can `xargs -n 1` over the result.
    cred = _load_cred(ns)
    keys = list_prefix(prefix=ns.prefix, cred=cred, max_keys=ns.max_keys)
    for key in keys:
        _emit(key)
    return 0


def _handle_make_bucket(ns: argparse.Namespace) -> int:
    """Handle ``make-bucket``: create a bucket (no-op if already owned).

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``bucket``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # make_bucket() is idempotent when the bucket already belongs to us.
    cred = _load_cred(ns)
    make_bucket(bucket=ns.bucket, cred=cred)
    return 0


def _handle_tempfile(ns: argparse.Namespace) -> int:
    """Handle ``tempfile``: print a fresh ``{s3_address, public_url}`` JSON pair.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``ext`` / ``prefix``).

    Returns
    -------
    int
        Process exit code (``0`` on success). Nothing is uploaded.
    """
    # remote_tempfile is a context manager: we enter it, print the key +
    # url pair, then exit immediately. Since no object was uploaded inside
    # the block, the auto-cleanup is a no-op (delete of a missing key is
    # idempotent). Useful to pre-compute an upload target for a caller
    # that will do the upload itself.
    cred = _load_cred(ns)
    with remote_tempfile(cred, ext=ns.ext or "", prefix=ns.prefix or "") as (addr, url):
        # JSON is the natural shape for a (key, url) pair.
        _emit(json.dumps({"s3_address": addr, "public_url": url}, indent=2))
    return 0


def _handle_strip_path(ns: argparse.Namespace) -> int:
    """Handle ``strip-path``: print the key part of an ``s3://`` address.

    Parameters
    ----------
    ns : argparse.Namespace
        Parsed args (``config`` / ``address``).

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    # strip_s3_path() returns the key part of an s3:// address (or of a
    # bare key). Handy in shell pipelines.
    cred = _load_cred(ns)
    _emit(strip_s3_path(ns.address, cred))
    return 0


# ---------------------------------------------------------------------------
# Parser construction
#
# One helper per subcommand keeps ``build_parser`` readable and lets the
# click twin (:mod:`bucket_helper.cli_click`) mirror the exact same flag
# names without any risk of drift.
# ---------------------------------------------------------------------------


def _add_common_config(p: argparse.ArgumentParser) -> None:
    """Attach the shared ``--config`` option to a subparser.

    Parameters
    ----------
    p : argparse.ArgumentParser
        The subparser to extend in place.
    """
    # Every subcommand needs the config path.
    p.add_argument(
        "--config",
        default=None,
        help="Path to settings.yaml (or .json), or a folder holding one. Empty = env-only.",
    )


def _add_upload(sub: argparse._SubParsersAction) -> None:
    """Register the ``upload`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("upload", help="Upload a local file to S3.")
    _add_common_config(p)
    p.add_argument("--input", required=True, help="Local file path.")
    p.add_argument(
        "--key",
        default=None,
        help="Destination — 's3://bucket/key' or a key under the default bucket. "
        "Empty = auto-generate a hex-hash key under cred['s3_prefix'].",
    )
    p.add_argument(
        "--content-type",
        default=None,
        dest="content_type",
        help="Override the S3 Content-Type header (e.g. application/json).",
    )
    p.set_defaults(func=_handle_upload)


def _add_download(sub: argparse._SubParsersAction) -> None:
    """Register the ``download`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("download", help="Download an S3 object to a local path.")
    _add_common_config(p)
    p.add_argument(
        "--key", required=True, help="Source — 's3://bucket/key' or a key under the default bucket."
    )
    p.add_argument("--output", required=True, help="Destination local file path.")
    p.set_defaults(func=_handle_download)


def _add_delete(sub: argparse._SubParsersAction) -> None:
    """Register the ``delete`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("delete", help="Delete an S3 object (idempotent).")
    _add_common_config(p)
    p.add_argument(
        "--key",
        required=True,
        help="Object address — 's3://bucket/key' or a key under the default bucket.",
    )
    p.set_defaults(func=_handle_delete)


def _add_exists(sub: argparse._SubParsersAction) -> None:
    """Register the ``exists`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("exists", help="Return exit code 0 if the object exists, 1 otherwise.")
    _add_common_config(p)
    p.add_argument(
        "--key",
        required=True,
        help="Object address — 's3://bucket/key' or a key under the default bucket.",
    )
    p.set_defaults(func=_handle_exists)


def _add_list(sub: argparse._SubParsersAction) -> None:
    """Register the ``list`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("list", help="List keys under a prefix in the default bucket.")
    _add_common_config(p)
    p.add_argument(
        "--prefix", required=True, help="Key prefix (e.g. 'uploads/' or empty for root)."
    )
    p.add_argument(
        "--max-keys",
        type=int,
        default=1000,
        dest="max_keys",
        help="Cap on the number of returned keys (default 1000).",
    )
    p.set_defaults(func=_handle_list)


def _add_make_bucket(sub: argparse._SubParsersAction) -> None:
    """Register the ``make-bucket`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("make-bucket", help="Create a bucket (no-op if it already exists).")
    _add_common_config(p)
    p.add_argument("--bucket", required=True, help="Bucket name to create.")
    p.set_defaults(func=_handle_make_bucket)


def _add_tempfile(sub: argparse._SubParsersAction) -> None:
    """Register the ``tempfile`` subcommand and its flags on ``sub``."""
    p = sub.add_parser(
        "tempfile",
        help="Emit a unique random key + public URL (JSON). Does NOT upload anything.",
    )
    _add_common_config(p)
    p.add_argument(
        "--ext",
        default=None,
        help="File extension for the generated name (with or without leading dot).",
    )
    p.add_argument(
        "--prefix", default=None, help="Extra prefix path under the bucket / default prefix."
    )
    p.set_defaults(func=_handle_tempfile)


def _add_strip_path(sub: argparse._SubParsersAction) -> None:
    """Register the ``strip-path`` subcommand and its flags on ``sub``."""
    p = sub.add_parser("strip-path", help="Extract the key part of an 's3://bucket/key' address.")
    _add_common_config(p)
    p.add_argument("--address", required=True, help="Full 's3://bucket/key' URI or a bare key.")
    p.set_defaults(func=_handle_strip_path)


def build_parser() -> argparse.ArgumentParser:
    """
    Assemble the top-level ``bucket-helper`` argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Fully wired parser with every subcommand attached.
    """
    parser = argparse.ArgumentParser(
        prog="bucket-helper",
        description=(
            "Bucket Helper — CLI for AWS S3 and S3-compatible object storage "
            "(MinIO / R2 / B2 / Spaces / Wasabi). Upload / download / list / "
            "exists / delete / make-bucket / tempfile / strip-path."
        ),
    )
    # Every non-trivial CLI benefits from `--version` — cheap to add and
    # oncall people always look for it. We resolve it lazily to avoid a
    # circular import if importlib.metadata blows up in some edge case.
    try:
        from importlib.metadata import version as _pkg_version

        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {_pkg_version('bucket-helper')}",
        )
    except Exception:  # pragma: no cover — never fatal
        pass

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # Register every subcommand. Order matters for help output only.
    _add_upload(subparsers)
    _add_download(subparsers)
    _add_delete(subparsers)
    _add_exists(subparsers)
    _add_list(subparsers)
    _add_make_bucket(subparsers)
    _add_tempfile(subparsers)
    _add_strip_path(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Entry point invoked by ``bucket-helper`` (see ``[project.scripts]``).

    Parameters
    ----------
    argv : sequence of str, optional
        Arguments to parse. Defaults to ``sys.argv[1:]`` when None.

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    # Every subparser sets ``func`` via ``set_defaults`` — no dispatch table
    # needed, argparse resolved it for us.
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
