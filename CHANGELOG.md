# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
