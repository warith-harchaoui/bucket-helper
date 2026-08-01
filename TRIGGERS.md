# TRIGGERS — bucket-helper

This is the user-facing, exhaustive catalogue of what `bucket-helper` can do and
the natural-language phrasings, commands, functions, and address cues that
should invoke it — whether you call it yourself or drive it as a
Claude Code / OpenCode **skill** (see [`skills/bucket-helper/SKILL.md`](skills/bucket-helper/SKILL.md)
and its [`references/triggers.md`](skills/bucket-helper/references/triggers.md)).

`bucket-helper` moves files to and from **AWS S3 and any S3-compatible object
storage** (MinIO, Cloudflare R2, Backblaze B2 S3 API, DigitalOcean Spaces,
Wasabi) via [boto3](https://boto3.amazonaws.com/). It is **remote by design** —
there is no local-first mode and no GUI. It does **not** sync directory trees,
mint presigned URLs, configure buckets (policies / lifecycle / versioning), or
edit file contents.

## The operations → how to invoke

| Intent | CLI | Library | API |
|--------|-----|---------|-----------|
| Upload a local file (auto-key if omitted) | `bucket-helper upload` | `upload` | `POST /upload` |
| Download an object to a local path | `bucket-helper download` | `download` | `POST /download` |
| Check existence (exit 0/1) | `bucket-helper exists` | `exists` | `POST /exists` |
| List keys under a prefix | `bucket-helper list` | `list_prefix` | `POST /list` |
| Delete an object (idempotent) | `bucket-helper delete` | `delete` | `POST /delete` |
| Create a bucket (no-op if owned) | `bucket-helper make-bucket` | `make_bucket` | `POST /make-bucket` |
| Unique random key + public URL, auto-clean | `bucket-helper tempfile` | `remote_tempfile` | `POST /tempfile` |
| Key part of an `s3://` address | `bucket-helper strip-path` | `strip_s3_path` | `POST /strip-path` |
| Load credentials (JSON / YAML / .env / env) | *(implicit `--config`)* | `credentials` | *(request fields / `BUCKET_HELPER_CONFIG`)* |
| Raw boto3 client (advanced) | — | `get_client_s3` | — |

Every operation is also reachable through the click CLI (`bucket-helper-click …`,
same flags). There is **no GUI**.

## Natural-language phrasings that should fire

- **Upload**: "upload / put / push this file to S3 / my bucket", "store this on
  MinIO / R2 / B2 / Spaces / Wasabi", "save this to s3://bucket/key".
- **Download**: "download s3://…", "fetch this key locally", "pull this down".
- **Exists**: "does this key exist", "is s3://… already there".
- **List**: "list keys under this prefix", "what's in my bucket / this folder".
- **Delete**: "delete / remove this object", "clean up s3://…".
- **Make bucket**: "create / make a bucket".
- **Stage-and-share**: "give me a throwaway remote key + public URL that
  auto-deletes", "stage this and hand me a shareable URL".
- **Strip path**: "get the key part of s3://bucket/key".
- **Credentials**: "use my s3_config.json", "read the bucket creds from env".
- **Surfaces**: "run the bucket-helper API server", "install bucket-helper".

## Address / endpoint cues

- An `s3://bucket/key` URI (with a read/write intent).
- An S3 endpoint: `*.amazonaws.com`, `*.r2.cloudflarestorage.com`,
  `*.backblazeb2.com`, `*.digitaloceanspaces.com`, `*.wasabisys.com`, a MinIO
  `:9000` endpoint.
- An `s3_config.json` / `s3_config.yaml` file in play.

## When NOT to use bucket-helper (SKIP)

- **Non-S3-shaped storage** — Google Cloud Storage native API, Azure Blob
  native API (only their S3-compat gateways qualify), plain local filesystem, or
  **FTP / SFTP** (use [sftp-helper](https://github.com/warith-harchaoui/sftp-helper)).
- **Out-of-scope S3 features** — presigned URLs, bucket policies / IAM / ACLs,
  lifecycle rules, versioning, replication, CORS, encryption, storage-class
  transitions → use boto3 or the provider console directly.
- **Directory-tree sync / mirroring** — "sync this folder to the bucket",
  "mirror", rsync-style → use `rclone`, `aws s3 sync`, or `mc mirror`.
- **Data versioning** — DVC, lakeFS.
- **File-content work** — parsing / transforming / transcoding the bytes.
- **A GUI or local-first mode** — does not exist here, by design.

## See also

- [`README.md`](README.md) — features, install, quick start.
- [`LISEZMOI.md`](LISEZMOI.md) — French mirror.
- [`EXAMPLES.md`](EXAMPLES.md) — runnable recipes.
- [`LANDSCAPE.md`](LANDSCAPE.md) — competitive positioning.
- [`skills/README.md`](skills/README.md) — installing this as an agent skill.
