# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-08

### Added

- **MCP surface** (`bucket_helper.mcp`, `[mcp]` extra, entry point
  `bucket-helper-mcp`): exposes the existing FastAPI app as MCP tools via
  `fastapi-mcp`, mirroring the pattern already shipped in `standpoint` /
  `vocal-helper` / `md2star` / `os-helper`. Closes the CLI/API/MCP surface
  gap for bucket-helper flagged in `ai-helpers/.private/do.md` §7.

## [1.0.0] - 2026-08-02

First stable release. The storage API (`upload` / `download` / `list` /
`delete` / `exists` / `make_bucket` / `remote_tempfile`, plus the `credentials`
loader) has been stable across the 0.x line; 1.0.0 commits to it and adopts the
hardened suite foundation.

### Changed

- **Requires os-helper 2.x** (`os-helper>=2.0.0,<3`, was `>=1.5.3`), adopting the
  stable AI Helpers foundation for logging and file management.
- Development status promoted to Production/Stable.
- **CI is now a real gate.** The lint job dropped its `continue-on-error: true`
  and `ruff check . || true` — both silently swallowed lint failures — and now
  runs a blocking `ruff check .` plus `ruff format --check .`. The test matrix
  is trimmed to a single Python (the full sweep runs locally before push), and
  the vestigial `ffmpeg` system-deps step (a template leftover; bucket-helper
  never touches ffmpeg) is removed.

### Fixed

- README / LISEZMOI install commands no longer self-pin to a git tag (`@v0.4.0`);
  they use `pip install bucket-helper`, which always resolves to the latest
  published release.

### Added

- `tests/test_readme_install_pin.py` guards against the stale git self-pin ever
  returning to any Markdown file.

## [0.4.1] - 2026-08-01

### Removed

- **Agent skill dropped from the public repo.** Without an MCP surface,
  the Claude/OpenCode skill (`skills/`) no longer earns its keep as public
  distribution — moved to the gitignored `.private/skills/` (kept locally
  as reference, never published). `TRIGGERS.md` stays public; its
  skill-specific framing, install instructions, and dead `skills/` links
  are removed.

## [0.4.0] - 2026-08-01

### Removed

- **MCP surface dropped.** `fastapi-mcp`'s latest release (0.4.0) is
  incompatible with the latest `mcp` SDK (`Server.__init__()` signature
  mismatch), breaking CI with no available version pairing to pin around.
  Removed `bucket_helper/mcp.py`, the `bucket-helper-mcp` entry point, the
  `mcp` extra, and every doc/skill mention. The library, both CLIs, and the
  FastAPI HTTP surface are unaffected — bucket-helper now ships **three**
  surfaces instead of four (it never had a GUI, by design).

## [0.3.0] - 2026-07-20

### Added

- **Agent skill (Claude + OpenCode).** New `skills/bucket-helper/` package with a
  trigger-rich `SKILL.md` (third-person description, exhaustive enforced TRIGGER
  clause + SKIP rules) and progressive-disclosure `references/`
  (`cli-reference.md`, `surfaces.md`, `triggers.md`), plus `skills/README.md`
  with symlink install steps for both `~/.claude/skills/` and
  `~/.opencode/skills/`. Lets an AI agent discover and drive the toolkit without
  the user opening a terminal.
- **Root `TRIGGERS.md`.** User-facing, auditable catalogue of the phrasings,
  commands, functions, and `s3://` / endpoint cues that invoke bucket-helper,
  with explicit SKIP boundaries (non-S3 clouds, SFTP → sftp-helper, tree sync →
  rclone / `aws s3 sync`, presigned URLs / bucket config → boto3). Referenced
  from README and LISEZMOI.

### Changed

- **FastAPI OpenAPI `version` now resolves from installed package metadata**
  (`importlib.metadata.version`) instead of a hardcoded literal, so it tracks
  `pyproject.toml` and no longer drifts (was stuck at `0.2.2`).
- README and LISEZMOI gain Skills + Triggers navigation; source-install pins
  refreshed to `v0.3.0`.

### Notes

- No GUI and no local-first badge — by design. bucket-helper moves data to
  *remote* object storage, so a local-first claim would be misleading.
- Public API unchanged and fully backward-compatible.

## [0.2.5] - 2026-07-20

### Changed

- **Upload and download now show a progress bar.** `upload` and `download` wire
  boto3's transfer `Callback` into the shared `os_helper.progress_bar` (byte
  scaled, ETA, auto-quiet on a non-TTY), so moving a large object gives live
  feedback instead of a silent stall. Download reads the object size via a cheap
  `head_object` for the bar total (falls back to open-ended if HEAD is denied).
  Requires `os-helper>=1.5.3`.

## [0.2.4] - 2026-07-15

### Documentation

- Harmonize README/LISEZMOI to the AI Helpers common structure (single H1,
  PyPI + source install paths, refreshed pins to v0.2.4); no code changes.

## [0.2.3] - 2026-07-14

### Maintenance

- Apply the project coding standards across the package and `tests/`:
  Numpy-style docstrings on every function/class (including private and
  nested helpers), full type annotations with `from __future__ import
  annotations`, and comment density raised above the floor in every
  module. No public API or behavior changes.
- Route library logging through the os-helper logging surface
  (`osh.info/warning/error`) and adopt os-helper path/file utilities
  more widely; pin `os-helper>=1.5.0`.
- Refresh the project logo asset.


## [0.2.2] - 2026-07-08

### Documentation

- Cross-platform Install prerequisites (macOS / Ubuntu / Windows).

## [0.2.1] - 2026-07-07

### Documentation

- Establish suite-wide Python coding-style mandate in `CONTRIBUTING.md`:
  numpy-style docstrings on every function and class, module-level
  docstring header (with usage example + author), full type annotations,
  generous explanatory comments.
- `EXAMPLES.md` cookbook present at the repo root and linked from
  README + LISEZMOI.
- `print(...)` in docs (EXAMPLES.md / README / LISEZMOI) is followed by
  a `#`-comment showing the expected output (doctest / REPL style);
  library `.py` code uses `osh.info` / `osh.warning` / `osh.error`
  instead of bare `print`.
- Every `brew install <pkg>` mention is paired with a brew.sh hint when
  not already obvious from context.
- `.gitignore` updated to drop accidental `*config.json` commits while
  keeping `*config.json.example` templates tracked.
- Ship `s3_config.json.example` template at the repo root for first-time setup.

### Changed

- Add GitHub Actions CI.

## [0.1.0] - 2026-06-29

First release under the `bucket-helper` name (formerly the
`s3-helper` repository, renamed for PyPI naming-conflict reasons).

### Features at release

- `credentials(path)` — JSON / env loader for S3-compatible
  storage credentials (AWS, MinIO, R2, B2, Spaces, Wasabi).
- `get_client_s3(cred)` — boto3 client factory respecting custom
  endpoints and region overrides.
- CRUD: `upload`, `download`, `delete`, `exists`, `list_prefix`,
  `make_bucket`.
- `remote_tempfile(cred, ext=...)` context manager for
  stage-and-share flows (mirrors `sftp-helper`).
- `strip_s3_path` URI helper.
- `moto`-backed unit tests; integration marker for hitting real
  endpoints.
