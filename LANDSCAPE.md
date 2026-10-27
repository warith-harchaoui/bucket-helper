# Landscape

[🇫🇷 PAYSAGE.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/PAYSAGE.md) · 🇬🇧 English

Related and competing Python libraries / CLIs in the "talk to S3-shaped
object storage" space, benchmarked against `bucket-helper`. Ratings are
⭐ (1) to ⭐⭐⭐⭐⭐ (5), scored on `bucket-helper`'s intended job:
everyday object-storage plumbing for AI + data pipelines (config-file
credentials, upload / download / list / exists / delete, path-style
MinIO / R2 / B2 / Spaces / Wasabi support, stage-and-share temp keys
with auto-cleanup). A library optimised for a very different job (e.g.
low-level SDK, provider-native CLI) is not penalised; the score
just reflects fit to *this* niche.

## At a glance

<!-- TABLE:START -->
| Object Storage | Multi-provider S3 | Config-file credentials | Simple CRUD | Stage-and-share temp keys | S3-compatible URLs | Multi-surface | Light install | AI-pipeline ergonomics |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **bucket-helper** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| boto3 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| botocore | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| minio | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| s3fs | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| cloudpathlib | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| smart_open | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| apache-libcloud | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| awscli | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| gsutil | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| fsspec | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
<!-- TABLE:END -->

## Positioning map

<!-- FIGURE:START -->
2D representation of the table above.

![Positioning map](https://raw.githubusercontent.com/warith-harchaoui/bucket-helper/main/assets/landscape.png)

The map is a 2-D summary of the eight criteria, so read it as a shape, not a scoreboard. `bucket-helper` is at the top-right corner. The axes read **Horizontal — Adaptable ↔ Accessible** and **Vertical — Streamlined ↔ Versatile**.
<!-- FIGURE:END -->

## Positioning

`bucket-helper` deliberately sits at the intersection of **`sftp-helper`
ergonomics** (config-file credentials with JSON / YAML / .env fallback,
uniform `credentials()` loader, path-based API, `remote_tempfile`
auto-cleanup) and **`boto3`'s reach** (talks to any S3-compatible
endpoint, not just AWS). It is a productivity layer *on top* of boto3,
not a replacement: you can always drop into raw `boto3` via
`get_client_s3(cred)` when you need a paginator, a presigned URL or a
server-side encryption knob that the helper does not wrap.

This toolkit is **remote object storage by design**: there is no
local-first mode and no GUI. It exists to move bytes to and from a
bucket, not to stand in for the disk.

The main differentiator against `boto3` alone is (a) the config loader
that unifies credential sources (JSON, YAML, `.env`, environment) across
a fleet of storage backends under one dict-shaped API, (b) the
`remote_tempfile` context manager that removes the "did I forget to
delete that S3 blob?" foot-gun by staging a file under a unique random
key that auto-deletes on block exit, and (c) the multi-surface exposure
(one click CLI + FastAPI HTTP + MCP tools) shared with the rest of the
AI-Helpers family: same function signatures, no drift.

The sibling `sftp-helper` is absent from the at-a-glance grid on purpose.
It speaks SFTP rather than S3, so the multi-provider and S3-URL columns
have nothing to measure on it; scoring it would compare two different
jobs. It is still the right answer whenever the remote is an SFTP host —
see *When to pick what* below.

## When to pick what

- **`bucket-helper`**: quick, path-based CRUD against S3 or any
  S3-compatible endpoint in a Python service; stage-and-share flows
  where automatic remote cleanup matters; when you already use
  `os-helper` / `sftp-helper` and want the same shape for object
  storage.
- **`boto3` / `botocore`**: you need a low-level SDK feature we do not
  wrap (presigned URLs, server-side encryption, multipart-copy,
  SelectObjectContent, …); `botocore` when you want the bare transport
  layer under `boto3`.
- **`s3fs` / `fsspec`**: you want an `fsspec`-native filesystem so
  `pandas` / `dask` / `polars` can read directly from `s3://…`.
- **`awscli` / `gsutil`**: DevOps / sysadmin work from the shell: bulk
  syncs, scripted copies, cron-driven backups. Better ergonomics than
  any Python library for that particular job.
- **`minio` / `cloudpathlib` / `apache-libcloud`**: a single narrow
  fit: the vendor's own MinIO SDK, `pathlib.Path`-style cloud paths, or
  a broad multi-cloud abstraction that reaches well beyond S3.
- **`smart_open`**: you only need `open("s3://…")` and nothing else.
- **`sftp-helper`** (not in the grid): the remote is an SFTP host, not a
  bucket. Nothing here will reach it — `bucket-helper` speaks the S3 API
  and only the S3 API.

## Sources and as-of date

**As of 2026-10-27.**

- **What the stars are.** Each column is this document's own reading of
  how well a project fits `bucket-helper`'s declared niche — everyday
  object-storage plumbing for AI and data pipelines — not a benchmark.
  No timing, throughput or memory figure was measured for any row,
  including `bucket-helper`'s own. A low score means "aimed elsewhere",
  never "slower".
- **Where the numbers live.** The grid above is generated from
  [`assets/landscape.csv`](https://github.com/warith-harchaoui/bucket-helper/blob/main/assets/landscape.csv)
  (French: `assets/paysage.csv`), which `gen_landscape.py` also reads to
  draw the positioning map. Edit the CSV, not the rendered table.
- **The `bucket-helper` row** was scored by reading this repository at
  `v1.3.0` — the eight CLI verbs, the eight matching HTTP endpoints, the
  public functions re-exported from `bucket_helper/__init__.py`, and the
  dependency list in `pyproject.toml`.
- **The other rows** were scored from each project's own published
  documentation, not from release notes or third-party comparisons:
  [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html),
  [botocore](https://github.com/boto/botocore),
  [minio-py](https://github.com/minio/minio-py),
  [s3fs](https://github.com/fsspec/s3fs),
  [cloudpathlib](https://github.com/drivendataorg/cloudpathlib),
  [smart_open](https://github.com/piskvorky/smart_open),
  [Apache Libcloud](https://libcloud.apache.org/),
  [AWS CLI](https://github.com/aws/aws-cli),
  [gsutil](https://cloud.google.com/storage/docs/gsutil),
  [fsspec](https://github.com/fsspec/filesystem_spec).
- **No version numbers are quoted for the other projects**, deliberately:
  a pinned competitor version in a document nobody re-reads is the claim
  most likely to be wrong a year from now. The scores describe the shape
  of each tool, which moves far more slowly.
- **One row is moving.** Google's own documentation carries a
  [Transition from gsutil to gcloud storage](https://cloud.google.com/storage/docs/gsutil/gcloud-storage)
  page, so the `gsutil` row describes a tool its vendor is steering users
  off. Read it as the historical shell client it is.
