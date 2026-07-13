# LANDSCAPE

Related and competing Python libraries / CLIs in the "talk to S3-shaped
object storage" space, benchmarked against `bucket-helper`. Ratings are
`⭐️` (1) to `⭐️⭐️⭐️⭐️⭐️` (5), scored on `bucket-helper`'s intended job —
everyday object-storage plumbing for AI + data pipelines (config-file
credentials, upload / download / list / exists / delete, path-style
MinIO / R2 / B2 / Spaces / Wasabi support, stage-and-share temp keys
with auto-cleanup). A library optimised for a very different job (e.g.
low-level SDK, DVC-style data versioning) is not penalised — the score
just reflects fit to *this* niche.

## At a glance

| Library / project | Multi-provider (AWS + MinIO + R2 + B2 + Spaces + Wasabi) | Config-file credentials (JSON / YAML / .env) | Simple CRUD (upload / download / delete / exists / list) | Stage-and-share temp keys (auto-cleanup) | S3-compatible URLs (`s3://…` + `https://…` builder) | Multi-surface (library + CLI + FastAPI + MCP) | Light install (pure-Python wheels only) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **bucket-helper** *(this project)* | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ (`remote_tempfile`) | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ (argparse + click + FastAPI + MCP) | ⭐️⭐️⭐️⭐️⭐️ |
| boto3 (raw AWS SDK) | ⭐️⭐️⭐️⭐️⭐️ (any `endpoint_url`) | ⭐️⭐️ (INI-only + env) | ⭐️⭐️ (verbose: paginators, ExtraArgs, quirks) | ⭐️ (none) | ⭐️⭐️ (no path builder helpers) | ⭐️ (SDK only) | ⭐️⭐️⭐️⭐️⭐️ |
| aioboto3 | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️ (inherits boto3) | ⭐️⭐️ (async surface, same verbosity) | ⭐️ | ⭐️⭐️ | ⭐️ | ⭐️⭐️⭐️⭐️ |
| s3fs / fsspec | ⭐️⭐️⭐️⭐️ | ⭐️⭐️ (INI + env) | ⭐️⭐️⭐️⭐️ (feels like a filesystem) | ⭐️⭐️ (`with fs.open(..., "wb"):`, no auto-clean) | ⭐️⭐️⭐️ | ⭐️⭐️ (Python API only) | ⭐️⭐️⭐️⭐️ |
| MinIO Python SDK | ⭐️⭐️⭐️ (MinIO + AWS + R2 mostly) | ⭐️⭐️ | ⭐️⭐️⭐️⭐️ (put_object / get_object / …) | ⭐️ | ⭐️⭐️⭐️ | ⭐️ | ⭐️⭐️⭐️⭐️⭐️ |
| AWS CLI (`aws s3` / `aws s3api`) | ⭐️⭐️⭐️⭐️ (`--endpoint-url`) | ⭐️⭐️ (INI + env) | ⭐️⭐️⭐️⭐️ | ⭐️ | ⭐️⭐️ | ⭐️⭐️ (CLI only) | ⭐️⭐️⭐️ (bundled runtime) |
| `mc` (MinIO client) | ⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️ (alias file) | ⭐️⭐️⭐️⭐️⭐️ (rsync-like ergonomics) | ⭐️ | ⭐️⭐️⭐️ | ⭐️⭐️ (CLI only) | ⭐️⭐️⭐️⭐️⭐️ (single binary) |
| rclone | ⭐️⭐️⭐️⭐️⭐️ (any backend) | ⭐️⭐️⭐️⭐️ (rich config) | ⭐️⭐️⭐️⭐️⭐️ (sync / copy / lsjson) | ⭐️ | ⭐️⭐️⭐️ | ⭐️⭐️⭐️ (CLI + HTTP + rc) | ⭐️⭐️⭐️⭐️⭐️ (single binary) |
| DVC (S3 remote) | ⭐️⭐️⭐️ (any S3 endpoint) | ⭐️⭐️⭐️ | ⭐️⭐️ (versioning-first, not raw CRUD) | ⭐️ | ⭐️⭐️ | ⭐️⭐️ (CLI + Python) | ⭐️⭐️⭐️ |
| smart_open | ⭐️⭐️⭐️⭐️ | ⭐️⭐️ (env) | ⭐️⭐️⭐️ (open() over `s3://`) | ⭐️ | ⭐️⭐️⭐️ | ⭐️ | ⭐️⭐️⭐️⭐️⭐️ |
| sftp-helper *(sibling)* | n/a (SFTP, not S3) | ⭐️⭐️⭐️⭐️⭐️ (same loader) | ⭐️⭐️⭐️⭐️⭐️ | ⭐️⭐️⭐️⭐️⭐️ (`remote_tempfile`) | n/a | ⭐️⭐️⭐️ (library + CLI) | ⭐️⭐️⭐️⭐️⭐️ |

## Positioning

`bucket-helper` deliberately sits at the intersection of **`sftp-helper`
ergonomics** (config-file credentials with JSON / YAML / .env fallback,
uniform `credentials()` loader, path-based API, `remote_tempfile`
auto-cleanup) and **`boto3`'s reach** (talks to any S3-compatible
endpoint, not just AWS). It is a productivity layer *on top* of boto3,
not a replacement — you can always drop into raw `boto3` via
`get_client_s3(cred)` when you need a paginator, a presigned URL or
server-side encryption knob that the helper does not wrap.

The main differentiator against `boto3` alone is (a) the config loader
that unifies credential sources across a fleet of storage backends
under one dict-shaped API, (b) the `remote_tempfile` context manager
that removes the "did I forget to delete that S3 blob?" foot-gun, and
(c) the multi-surface exposure (argparse CLI + click CLI + FastAPI HTTP
+ MCP tools) shared with the rest of the AI-Helpers family.

## When to pick what

- **`bucket-helper`** — quick, path-based CRUD against S3 or any
  S3-compatible endpoint in a Python service; stage-and-share flows
  where automatic remote cleanup matters; when you already use
  `os-helper` / `sftp-helper` and want the same shape for object
  storage.
- **`boto3`** — you need a boto3 feature we do not wrap (presigned URLs,
  server-side encryption, multipart-copy, SelectObjectContent, …).
- **`s3fs` / `fsspec`** — you want an `fsspec`-native filesystem so
  `pandas` / `dask` / `polars` can read directly from `s3://…`.
- **`rclone` / `mc`** — DevOps / sysadmin work: bulk syncs, cross-cloud
  copies, cron-driven backups. Better ergonomics than any Python
  library for that particular job.
- **`DVC`** — you want *data versioning*, not just object storage.
- **`smart_open`** — you only need `open("s3://…")` and nothing else.
