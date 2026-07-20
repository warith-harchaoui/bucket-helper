# bucket-helper CLI reference

Full command surface for the `bucket-helper` skill. The argparse CLI
(`bucket-helper`) ships with the base package; the click twin
(`bucket-helper-click`, `[cli]` extra) mirrors the exact same subcommand and
flag names, so anything below works for both by swapping the program name.

Every subcommand takes `--config` — a path to `s3_config.json` / `s3_config.yaml`,
a folder holding one, or omitted for environment-only credentials. Under the
hood each command calls `bucket_helper.credentials(...)`, so the same precedence
order applies (JSON → YAML → `.env` → environment).

## Subcommands

| Subcommand | Purpose | Flags |
|------------|---------|-------|
| `upload` | Send a local file to S3 | `--config --input --key --content-type` |
| `download` | Fetch an S3 object to a local path | `--config --key --output` |
| `delete` | Delete an S3 object (idempotent) | `--config --key` |
| `exists` | Probe existence (exit code 0/1) | `--config --key` |
| `list` | List keys under a prefix | `--config --prefix --max-keys` |
| `make-bucket` | Create a bucket (no-op if owned) | `--config --bucket` |
| `tempfile` | Emit a unique random key + public URL (JSON); uploads nothing | `--config --ext --prefix` |
| `strip-path` | Extract the key part of an `s3://bucket/key` address | `--config --address` |

`bucket-helper --version` and `bucket-helper <sub> --help` work for every
subcommand. The click twin is `bucket-helper-click <sub> …` with identical flags.

## Flag details

### upload
- `--input` (required) local file path. Must exist and be non-empty.
- `--key` destination — a full `s3://bucket/key` URI or a bare key under the
  default bucket. **Empty → auto-generate** a hex-hash name (with the input's
  extension) under `cred["s3_prefix"]`.
- `--content-type` override the S3 `Content-Type` header (e.g.
  `application/json`). Omit to let the server default.
- Prints the resulting `s3://bucket/key` URI to stdout.

### download
- `--key` (required) source — `s3://bucket/key` or a bare key.
- `--output` (required) destination local path. Parent dirs are created.
- Prints the local path to stdout on success.

### delete
- `--key` (required) `s3://bucket/key` or bare key.
- Idempotent: deleting a missing key still succeeds. Prints nothing.

### exists
- `--key` (required) `s3://bucket/key` or bare key.
- Prints `true` / `false` to stdout **and** mirrors it in the exit code
  (`0` = exists, `1` = missing), so shell `if bucket-helper exists …; then`
  works naturally.

### list
- `--prefix` (required) key prefix in the default bucket (e.g. `uploads/`, or
  empty for the bucket root).
- `--max-keys` cap on returned keys (default `1000`).
- Prints one key per line to stdout — pipe with `xargs -n 1`.

### make-bucket
- `--bucket` (required) bucket name to create. Honors `cred["s3_region"]` for
  the `LocationConstraint` (us-east-1 gets none — an AWS quirk). No-op when the
  bucket already belongs to the caller.

### tempfile
- `--ext` extension for the generated random name (with or without leading dot).
- `--prefix` extra path segment under the bucket / `cred["s3_prefix"]`.
- Prints a JSON `{"s3_address": …, "public_url": …}` pair. **Uploads nothing** —
  it is a name generator (the auto-delete on exit is a no-op against a key that
  was never written). Useful to pre-compute an upload target.

### strip-path
- `--address` (required) full `s3://bucket/key` URI or a bare key.
- Prints the key part (drops the `s3://bucket/` prefix). Compatible with
  sftp-helper's `strip_sftp_path`.

## Output contract (for scripting)

- `upload` prints the single `s3://bucket/key` URI.
- `download` prints the local output path.
- `exists` prints `true`/`false` and sets exit code `0`/`1`.
- `list` prints one key per line.
- `tempfile` prints a 2-key JSON object (`s3_address`, `public_url`).
- `strip-path` prints the key.
- `delete` / `make-bucket` print nothing on success (exit `0`).

Result output goes to **stdout**; diagnostics (via the os-helper logging
surface) go to **stderr** and are level-gated — so piping the result never
swallows a log line and vice versa.

## Address forms accepted everywhere

- `s3://bucket/path/to/object` → explicit bucket + key.
- `path/to/object` (no scheme) → the default `cred["s3_bucket"]` + that key.
- A leading `/` on a bare key is stripped.
