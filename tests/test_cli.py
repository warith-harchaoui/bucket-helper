"""
Smoke tests for the command line — one door now, built with click.

These exercise the *parsing* layer: every subcommand is wired, every
``--help`` exits 0, and a library exception leaves the process as one
clean ``Error: …`` line rather than a traceback. The full round-trip
through moto-mocked S3 lives in ``test_bucket_helper.py``.

There used to be two CLIs here — argparse plus an optional click twin —
and every case was written twice so the pair could be checked for drift.
The twin is the only CLI now, so each case is asserted once, against the
thing that ships. ``click`` is a core dependency, so nothing is skipped.

Usage Example
-------------
>>> #   pytest tests/test_cli.py

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

# The verbs the CLI must expose. Kept as a module-level constant so a verb
# quietly disappearing from the group fails here rather than in a user's shell.
EXPECTED_SUBCOMMANDS = {
    "upload",
    "download",
    "delete",
    "exists",
    "list",
    "make-bucket",
    "tempfile",
    "strip-path",
}


def test_group_has_expected_subcommands():
    """The click group exposes every verb the library promises."""
    from bucket_helper.cli import cli

    assert EXPECTED_SUBCOMMANDS.issubset(set(cli.commands.keys()))


def test_help_exits_zero():
    """``bucket-helper --help`` exits 0 and names itself."""
    from bucket_helper.cli import cli

    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "bucket helper" in result.output.lower()


@pytest.mark.parametrize("sub", sorted(EXPECTED_SUBCOMMANDS))
def test_subcommand_help_exits_zero(sub):
    """Every subcommand's ``--help`` exits 0 — no wiring bug."""
    from bucket_helper.cli import cli

    result = CliRunner().invoke(cli, [sub, "--help"])
    assert result.exit_code == 0


def test_main_prints_clean_error_not_traceback(monkeypatch, capsys):
    """A library exception prints ``Error: …`` and exits 1, not a traceback.

    Drives ``main()`` — the real console-script entry point — rather than the
    bare ``cli`` group, because the wrapper is exactly the layer that turns the
    exception into one line on stderr. ``CliRunner.invoke(cli, …)`` bypasses it.
    """
    from bucket_helper.cli import main

    for k in ("S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET", "S3_HTTPS"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(
        "sys.argv", ["bucket-helper", "strip-path", "--address", "s3:///no-bucket-here"]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Error: ")
    assert "Traceback" not in captured.err
