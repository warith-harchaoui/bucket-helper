"""
Smoke tests for the argparse and click CLIs.

These tests exercise the CLI *parsing* layer — that every subcommand is
wired, every ``--help`` exits 0, and the two CLIs expose the same set of
verbs. The full round-trip through moto-mocked S3 lives in
``test_bucket_helper.py``.

Usage Example
-------------
>>> #   pytest tests/test_cli.py

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import pytest

# The click CLI needs the ``click`` runtime dep, which lives in the
# ``[cli]`` optional extra. Skip cleanly if it is not installed.
click = pytest.importorskip("click")

from click.testing import CliRunner  # noqa: E402

# The canonical list of subcommands both CLIs must expose. Kept as a
# module-level constant so a drift in either surface is caught by both
# the argparse and click parametrised tests.
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


def test_argparse_parser_builds_without_error():
    """Building the parser should never fail (imports, subcommand wiring)."""
    from bucket_helper.cli_argparse import build_parser

    parser = build_parser()
    # A parser with subcommands exposes them via a _SubParsersAction.
    subparsers_action = next(
        a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"
    )
    assert EXPECTED_SUBCOMMANDS.issubset(set(subparsers_action.choices.keys()))


def test_argparse_help_exits_zero(capsys):
    """``bucket-helper --help`` should exit with code 0 and print usage."""
    from bucket_helper.cli_argparse import main

    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "bucket-helper" in captured.out.lower()


@pytest.mark.parametrize("sub", sorted(EXPECTED_SUBCOMMANDS))
def test_argparse_subcommand_help_exits_zero(sub):
    """Every subcommand's ``--help`` should exit 0 (no wiring bug)."""
    from bucket_helper.cli_argparse import main

    with pytest.raises(SystemExit) as exc:
        main([sub, "--help"])
    assert exc.value.code == 0


def test_click_group_has_expected_subcommands():
    """The click group must expose the same subcommands as the argparse CLI."""
    from bucket_helper.cli_click import cli

    assert EXPECTED_SUBCOMMANDS.issubset(set(cli.commands.keys()))


def test_click_help_exits_zero():
    """``bucket-helper-click --help`` should exit 0."""
    from bucket_helper.cli_click import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "bucket helper" in result.output.lower()


@pytest.mark.parametrize("sub", sorted(EXPECTED_SUBCOMMANDS))
def test_click_subcommand_help_exits_zero(sub):
    """Every click subcommand's ``--help`` should exit 0."""
    from bucket_helper.cli_click import cli

    runner = CliRunner()
    result = runner.invoke(cli, [sub, "--help"])
    assert result.exit_code == 0
