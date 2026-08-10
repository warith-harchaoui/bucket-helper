"""
Bucket Helper — click-based command-line interface.

Twin of :mod:`bucket_helper.cli_argparse`: same public surface (identical
subcommand names, identical flag semantics), but implemented with
:mod:`click` so users who already have a click-native shell setup
(bash / zsh completion via ``click.shell_completion``, colored `--help`,
nested command groups) can plug it in without friction. Installed as
the ``bucket-helper-click`` entry point in ``pyproject.toml``.

Design notes
------------
- Subcommands mirror ``bucket-helper`` (the argparse twin) so both CLIs
  can be introspected identically by higher layers (FastAPI).
- Flags reuse the argparse names (``--input`` / ``--key`` / …) rather
  than the more idiomatic click positional style — consistency across
  the two CLIs beats micro-idiomaticity here.
- Errors from the library propagate unchanged; click handles the
  formatting.

Usage Example
-------------
>>> #   bucket-helper-click upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
>>> #   bucket-helper-click download    --config settings.yaml --key folder/uploaded.txt --output local.txt
>>> #   bucket-helper-click list        --config settings.yaml --prefix folder/
>>> #   bucket-helper-click tempfile    --config settings.yaml --ext json --prefix runs

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

try:
    import click
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The click CLI requires the [cli] extra. Install with: pip install 'bucket-helper[cli]'"
    ) from exc

# Same underlying functions as the argparse twin — one source of truth.
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
# Top-level group
#
# ``invoke_without_command=False`` forces the user to name a subcommand;
# ``context_settings`` widens the help output so long option lists stay
# readable on modern terminals.
# ---------------------------------------------------------------------------


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 100},
)
@click.version_option(package_name="bucket-helper", prog_name="bucket-helper-click")
def cli() -> None:
    """Bucket Helper — click twin of the argparse CLI. Same subcommands."""
    # Nothing to do at the group level — every subcommand carries its
    # own arguments and side effects.


# ---------------------------------------------------------------------------
# Shared option: --config
# ---------------------------------------------------------------------------


# Repeating the ``--config`` option across eight subcommands would be
# noisy — we define it once as a decorator and apply it everywhere.
def _config_option(f: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared ``--config`` click option to a command callback.

    Parameters
    ----------
    f : callable
        The click command callback to decorate.

    Returns
    -------
    callable
        The same callback with the ``--config`` option registered.
    """
    # Applying the decorator programmatically lets every subcommand share
    # one definition of ``--config`` instead of repeating it eight times.
    return click.option(
        "--config",
        default=None,
        type=click.Path(exists=False),
        help="Path to settings.yaml (or .json), or a folder holding one. Empty = env-only.",
    )(f)


# ---------------------------------------------------------------------------
# upload
#
# We name each click command explicitly (``cli.command("verb")``) so the
# subcommand name is stable regardless of the Python function name, which
# has to be suffixed (``upload_``, ``list_cmd`` …) to avoid shadowing the
# library-level import of the same verb (``from . import upload``).
# ---------------------------------------------------------------------------


@cli.command("upload")
@_config_option
@click.option(
    "--input", "input_", required=True, type=click.Path(exists=True), help="Local file path."
)
@click.option(
    "--key", default=None, help="Destination key or full 's3://bucket/key' URI (empty = auto)."
)
@click.option(
    "--content-type",
    default=None,
    help="Override the S3 Content-Type header (e.g. application/json).",
)
def upload_(config: str | None, input_: str, key: str | None, content_type: str | None) -> None:
    """Upload a local file to S3."""
    # Thin dispatch to the library.
    cred = credentials(config)
    uri = upload(local_path=input_, cred=cred, s3_address=key or "", content_type=content_type)
    click.echo(uri)


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------


@cli.command("download")
@_config_option
@click.option("--key", required=True, help="Source key or full 's3://bucket/key' URI.")
@click.option("--output", required=True, type=click.Path(), help="Destination local file path.")
def download_(config: str | None, key: str, output: str) -> None:
    """Download an S3 object to a local path."""
    cred = credentials(config)
    out = download(s3_address=key, local_path=output, cred=cred)
    click.echo(out)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@cli.command("delete")
@_config_option
@click.option("--key", required=True, help="Object address — 's3://bucket/key' or bare key.")
def delete_(config: str | None, key: str) -> None:
    """Delete an S3 object (idempotent)."""
    cred = credentials(config)
    delete(s3_address=key, cred=cred)


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------


@cli.command("exists")
@_config_option
@click.option("--key", required=True, help="Object address — 's3://bucket/key' or bare key.")
def exists_(config: str | None, key: str) -> None:
    """Return exit code 0 if the object exists, 1 otherwise."""
    cred = credentials(config)
    present = exists(s3_address=key, cred=cred)
    click.echo("true" if present else "false")
    if not present:
        sys.exit(1)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@cli.command("list")
@_config_option
@click.option("--prefix", required=True, help="Key prefix (e.g. 'uploads/').")
@click.option("--max-keys", type=int, default=1000, show_default=True, help="Cap on returned keys.")
def list_cmd(config: str | None, prefix: str, max_keys: int) -> None:
    """List keys under a prefix in the default bucket."""
    cred = credentials(config)
    for key in list_prefix(prefix=prefix, cred=cred, max_keys=max_keys):
        click.echo(key)


# ---------------------------------------------------------------------------
# make-bucket
# ---------------------------------------------------------------------------


@cli.command("make-bucket")
@_config_option
@click.option("--bucket", required=True, help="Bucket name to create.")
def make_bucket_cmd(config: str | None, bucket: str) -> None:
    """Create a bucket (no-op if it already exists)."""
    cred = credentials(config)
    make_bucket(bucket=bucket, cred=cred)


# ---------------------------------------------------------------------------
# tempfile
# ---------------------------------------------------------------------------


@cli.command("tempfile")
@_config_option
@click.option("--ext", default=None, help="File extension for the generated name.")
@click.option("--prefix", default=None, help="Extra prefix path under the bucket / default prefix.")
def tempfile_(config: str | None, ext: str | None, prefix: str | None) -> None:
    """Emit a unique random key + public URL (JSON). Does NOT upload anything."""
    cred = credentials(config)
    with remote_tempfile(cred, ext=ext or "", prefix=prefix or "") as (addr, url):
        click.echo(json.dumps({"s3_address": addr, "public_url": url}, indent=2))


# ---------------------------------------------------------------------------
# strip-path
# ---------------------------------------------------------------------------


@cli.command("strip-path")
@_config_option
@click.option("--address", required=True, help="Full 's3://bucket/key' URI or a bare key.")
def strip_path_cmd(config: str | None, address: str) -> None:
    """Extract the key part of an 's3://bucket/key' address."""
    cred = credentials(config)
    click.echo(strip_s3_path(address, cred))


if __name__ == "__main__":  # pragma: no cover
    cli()
