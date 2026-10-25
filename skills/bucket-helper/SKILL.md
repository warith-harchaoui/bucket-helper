---
name: bucket-helper
description: >-
  Move files to and from an S3-compatible object store — AWS S3, MinIO,
  Backblaze B2, Cloudflare R2, Scaleway, OVH, any endpoint the user
  configures. Upload a file, download an object, check whether a key exists,
  list a prefix, delete an object, create a bucket, mint a remote temporary
  path, and strip an `s3://` URL down to bucket and key. Credentials come from
  a YAML / JSON / .env config or the environment, never from the skill. Use
  when the user says "upload this to S3 / my bucket / MinIO / R2 / B2",
  "download this object", "does this key exist", "list what is in this
  prefix", "delete this object", "create a bucket", "give me the public URL
  for this file", or names `bucket-helper`,
  `bucket-helper-mcp`, `import bucket_helper as bh`, `s3://`, `boto3`. Do NOT
  use for SFTP transfer (sftp-helper), plain local file management
  (os-helper), or downloading from a public media URL (youtube-helper).
license: BSD-3-Clause
metadata:
  author: Warith Harchaoui
  package: bucket-helper
  suite: ai-helpers
  homepage: https://deraison.ai/ai-helpers
---

# bucket-helper — S3-compatible object storage

`bucket-helper` moves files between the machine and an S3-compatible bucket.
It is **the suite's honest exception to local-first**: its whole job is to put
data somewhere else. That somewhere is the endpoint *the user* configured —
there is no vendor default, no telemetry, no relay.

## ⚠️ Credentials and destructive calls

- **Credentials never live in this skill.** `credentials()` reads them, in
  precedence order, from a JSON / YAML config, a `.env`, then environment
  variables (via `os_helper.get_config`). Keys: `s3_access_key`,
  `s3_secret_key`, `s3_bucket`, `s3_https`.
- **Never print a secret back to the user**, never paste one into a command
  line, and never write one into a file the user did not name.
- **`delete` and `make-bucket` change someone else's storage.** Confirm the
  exact bucket and key with the user before calling them. An upload that
  overwrites an existing key is destructive too — check with `exists` first
  when the key looks like it might already be in use.

## Before anything: verify it is installed and configured

```bash
bucket-helper --help                 # the CLI (ships with the package)
python -c "import bucket_helper"     # library import check
bucket-helper exists SOME_KEY        # proves credentials resolve and the endpoint answers
```

Install:

```bash
pip install bucket-helper                  # core: library + click CLI
pip install 'bucket-helper[api]'           # + FastAPI HTTP surface
pip install 'bucket-helper[mcp]'           # + MCP tools over the same app
```

Configuration starts from the repo's `settings.yaml.example` — copy it, fill
it in, and keep it out of version control.

## What it does, and how to invoke it

| Intent | CLI | Library |
|---|---|---|
| Send a local file up | `bucket-helper upload` | `upload` |
| Bring an object down | `bucket-helper download` | `download` |
| Does this key exist | `bucket-helper exists` | `exists` |
| What is under this prefix | `bucket-helper list` | `list_prefix` |
| Remove an object | `bucket-helper delete` | `delete` |
| Create a bucket | `bucket-helper make-bucket` | `make_bucket` |
| A scratch key on the remote | `bucket-helper tempfile` | `remote_tempfile` |
| Split an `s3://` URL | `bucket-helper strip-path` | `strip_s3_path` |

Quick examples:

```bash
bucket-helper upload ./report.pdf reports/2026/report.pdf
bucket-helper exists reports/2026/report.pdf
bucket-helper list  reports/2026/
bucket-helper download reports/2026/report.pdf ./local.pdf
```

```python
import bucket_helper as bh

url = bh.upload("./report.pdf", "reports/2026/report.pdf")  # public URL, from s3_https
if bh.exists("reports/2026/report.pdf"):
    bh.download("reports/2026/report.pdf", "./local.pdf")
```

`upload` returns the public URL built from the configured `s3_https` base —
that URL, not the local path, is what you report back to the user.

For the full flag matrix, the config keys and the output contract, read
`references/cli-reference.md`. For the HTTP API and MCP tools, read
`references/surfaces.md`. For the exhaustive trigger list, read
`references/triggers.md`.

## Rules of thumb

- **Check before you overwrite.** `exists` is one cheap call; a silent
  overwrite of someone's object is not recoverable.
- **Confirm before `delete` and `make-bucket`.** Name the bucket and the exact
  key back to the user and wait for a yes.
- **Prefixes are not directories.** `list_prefix("a/b/")` matches by string
  prefix; a missing trailing slash will happily match `a/bc/` too.
- **`remote_tempfile` is for intermediates**, so a pipeline can stage
  something remotely without inventing key names that collide.
- **`strip_s3_path` exists so you stop parsing `s3://` URLs by hand** — bucket
  and key, correctly split, including keys that contain slashes.
- **Report the object URL and the byte count after a transfer** — do not
  re-upload to confirm.
