---
name: bucket-helper
description: >-
  Move files to and from AWS S3 and any S3-compatible object storage (MinIO,
  Cloudflare R2, Backblaze B2 S3 API, DigitalOcean Spaces, Wasabi) with the
  `bucket-helper` toolkit — upload a local file, download an object, check
  existence, list keys under a prefix, delete an object (idempotent), create a
  bucket, strip an `s3://bucket/key` URI down to its key, and stage-and-share a
  file under a unique random key that auto-deletes on block exit
  (`remote_tempfile`). One `credentials()` loader reads JSON / YAML / .env /
  environment. Exposed as a Python library (`import bucket_helper as bh`), two
  CLIs (`bucket-helper` argparse and `bucket-helper-click`), and a FastAPI HTTP
  surface. boto3-backed. Remote object storage by design — there is NO
  local-first mode and NO GUI.

  TRIGGER — any of: the user names an object-storage operation ("upload this
  file to S3 / my bucket / MinIO / R2 / B2 / Spaces / Wasabi", "put this on the
  bucket", "download s3://... / this key to a local file", "does this object /
  key exist in the bucket", "list the keys / objects under this prefix", "what's
  in my bucket / this folder on S3", "delete / remove this object / key",
  "create / make a bucket", "give me a temp remote key + public URL that cleans
  itself up", "stage this file and hand me a shareable URL", "strip the bucket
  off this s3:// URI / get the key part"); the user types or references a command
  (`bucket-helper`, `bucket-helper-click`, subcommands
  `upload|download|delete|exists|list|make-bucket|tempfile|strip-path`) or a
  library function (`credentials`, `upload`, `download`, `delete`, `exists`,
  `list_prefix`, `make_bucket`, `remote_tempfile`, `strip_s3_path`,
  `get_client_s3`); the user mentions an `s3://bucket/key` URI, an S3 endpoint
  URL (`*.amazonaws.com`, `*.r2.cloudflarestorage.com`, `*.backblazeb2.com`,
  `*.digitaloceanspaces.com`, `*.wasabisys.com`, a MinIO `:9000` endpoint) and
  wants to read/write it; the user has an `s3_config.json` / `s3_config.yaml`
  and wants to use it; the user wants the bucket-helper HTTP API server
  run, or asks how to install / run bucket-helper.

  SKIP when: the storage is NOT S3-shaped — Google Cloud Storage native API,
  Azure Blob Storage native API (use their SDKs; only their S3-compat gateways
  qualify), a plain local filesystem, or FTP/SFTP (use sftp-helper). Also skip
  for: presigned-URL generation / bucket policies / IAM / lifecycle rules /
  versioning / replication / CORS config (out of scope — use boto3 or the
  provider console directly); data-versioning workflows (DVC / lakeFS);
  syncing whole directory trees / rsync-style mirroring (use `rclone` / `aws s3
  sync` / `mc mirror`); and anything about the *contents* of a file (parsing,
  transforming, transcoding) rather than moving the file. bucket-helper moves
  objects; it does not sync trees, mint presigned URLs, or edit file contents.
---

# bucket-helper — S3 / S3-compatible object-storage plumbing

`bucket-helper` is a small, boto3-backed Python toolkit for the everyday job of
**moving files to and from remote object storage** in AI and data pipelines. It
is file-oriented and credential-driven: you give it a local path and/or an
`s3://bucket/key` (or bare key), plus a credentials dict, and it does the
transfer. The same functions are reachable three ways (library, two CLIs, HTTP
API) so an agent can pick whichever fits.

> **Remote by design.** bucket-helper's whole purpose is to move data to a
> *remote* bucket. There is no local-first mode and no GUI — do not look for a
> `/gui` route or a "local-first" promise. For the reasoning, this is the one
> AI-Helpers member where a local-first claim would be misleading.

## Before anything: verify it is installed

```bash
bucket-helper --version            # argparse CLI (always installed with the pkg)
python -c "import bucket_helper"   # library import check
```

If missing, install it (boto3 is a hard dependency; pure-Python wheels only):

```bash
pip install bucket-helper                 # core (credentials + CRUD + remote_tempfile)
pip install 'bucket-helper[cli]'          # + click CLI twin
pip install 'bucket-helper[api]'          # + FastAPI HTTP surface
```

No system package is required (boto3 ships as a pure-Python wheel). Unlike
ffmpeg-backed helpers, there is nothing to `brew install`.

## Credentials first

Every operation needs a credentials dict. Load it once with `credentials()`,
which reads (in precedence order) a JSON / YAML file, a folder holding one, a
`.env`, then environment variables — via `os_helper.get_config`.

```python
import bucket_helper as bh
cred = bh.credentials("s3_config.json")   # or a folder, or "" for env-only
```

Required keys: `s3_access_key`, `s3_secret_key`, `s3_bucket`, `s3_https`.
Optional: `s3_region`, `s3_endpoint_url` (set this for MinIO / R2 / B2 / Spaces
/ Wasabi), `s3_prefix`, `s3_use_path_style`, `s3_verify_ssl`. A ready-to-fill
`s3_config.json.example` is committed at the repo root. Full key reference in
`references/surfaces.md`.

## The nine operations

Same names across the library, both CLIs, and the API:

| Operation | CLI | Library function |
|-----------|-----|------------------|
| Upload a local file (auto-key if omitted) | `bucket-helper upload` | `upload` |
| Download an object to a local path | `bucket-helper download` | `download` |
| Check existence (exit 0/1) | `bucket-helper exists` | `exists` |
| List keys under a prefix | `bucket-helper list` | `list_prefix` |
| Delete an object (idempotent) | `bucket-helper delete` | `delete` |
| Create a bucket (no-op if owned) | `bucket-helper make-bucket` | `make_bucket` |
| Unique random key + public URL, auto-clean | `bucket-helper tempfile` | `remote_tempfile` |
| Key part of an `s3://` address | `bucket-helper strip-path` | `strip_s3_path` |
| Open a raw boto3 client (advanced) | — | `get_client_s3` |

Quick examples:

```bash
bucket-helper upload      --config s3_config.json --input local.txt --key folder/uploaded.txt
bucket-helper download    --config s3_config.json --key folder/uploaded.txt --output back.txt
bucket-helper exists      --config s3_config.json --key folder/uploaded.txt   # exit 0/1
bucket-helper list        --config s3_config.json --prefix folder/
bucket-helper delete      --config s3_config.json --key folder/uploaded.txt
bucket-helper make-bucket --config s3_config.json --bucket new-bucket
bucket-helper tempfile    --config s3_config.json --ext json --prefix runs
bucket-helper strip-path  --config s3_config.json --address s3://my-bucket/path/to/obj
```

```python
import bucket_helper as bh
cred = bh.credentials("s3_config.json")
uri = bh.upload("local.txt", cred, "folder/uploaded.txt")   # -> "s3://my-bucket/folder/uploaded.txt"
assert bh.exists(uri, cred)
bh.download(uri, "back.txt", cred)
for key in bh.list_prefix("folder/", cred):
    ...
bh.delete(uri, cred)

# Stage-and-share: unique key, deleted on block exit even on exception.
with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    # hand `public_url` to a downstream worker / webhook
# object is gone here — no manual cleanup
```

For the full flag matrix and every option, read `references/cli-reference.md`.
For the library API, the credentials schema, and the HTTP API,
read `references/surfaces.md`. For the exhaustive, auditable trigger list, read
`references/triggers.md`.

## Rules of thumb

- **Pick the operation from the intent, not the file type.** "put this on the
  bucket" → `upload`; "fetch s3://…" → `download`; "is it there?" → `exists`;
  "what's under this prefix?" → `list`; "get rid of it" → `delete`; "I need a
  throwaway remote key + URL" → `remote_tempfile`.
- **Addresses are flexible.** Every op accepts either a full `s3://bucket/key`
  URI or a bare key under `cred["s3_bucket"]`. `upload` with an empty key
  auto-generates a hex-hash name under `cred["s3_prefix"]`.
- **S3-compatible endpoints are first-class.** Set `cred["s3_endpoint_url"]`
  (and usually `s3_use_path_style="true"` for MinIO with a custom domain) —
  everything else is identical. See the provider→endpoint table in
  `references/surfaces.md`.
- **`delete` and `make_bucket` are idempotent.** Deleting a missing key returns
  True; creating a bucket you already own is a no-op.
- **`remote_tempfile` cleans up even on exception** — the object is deleted on
  block exit whether the body succeeds or raises.
- **After running, report the `s3://…` URI / local path / key list** the tool
  returned; do not re-run unless something failed.
- **This is REMOTE storage.** Uploads leave the machine and hit the configured
  bucket. There is no offline / local-first mode and no GUI — do not promise one.
