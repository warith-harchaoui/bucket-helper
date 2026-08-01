# bucket-helper non-CLI surfaces

`bucket-helper` exposes the same operations through four surfaces. The Python
library and argparse CLI are always available; the others live behind optional
extras. **There is no GUI** (unlike ffmpeg-backed AI-Helpers members): this is
remote object-storage plumbing, so there is no local audition bench and no
`/gui` route.

## Credentials schema

Every surface takes the same credentials dict, loaded by
`bucket_helper.credentials(config_path)` (JSON → YAML → `.env` → env, via
`os_helper.get_config`).

**Required keys**

| Key | Meaning |
|-----|---------|
| `s3_access_key` | Access key ID |
| `s3_secret_key` | Secret access key |
| `s3_bucket` | Default bucket name |
| `s3_https` | Base public URL for built object URLs (e.g. `https://my-bucket.s3.eu-west-3.amazonaws.com` or a CDN) — used by `remote_tempfile` to hand back a public URL |

**Optional keys**

| Key | Default | Notes |
|-----|---------|-------|
| `s3_region` | `us-east-1` | AWS region; mostly cosmetic for MinIO / R2 |
| `s3_endpoint_url` | empty (= AWS S3) | Set for S3-compatible backends (see table below) |
| `s3_prefix` | empty | Default key prefix used by `upload` / `remote_tempfile` when no destination is given |
| `s3_use_path_style` | `false` | `true` forces path-style addressing (`endpoint/bucket/key`) — typical for MinIO with a custom domain |
| `s3_verify_ssl` | `true` | `false` disables TLS verification — only for dev MinIO with a self-signed cert |

### Provider → `s3_endpoint_url`

| Provider | Endpoint |
|----------|----------|
| **AWS S3** | leave empty / unset (boto3 picks `s3.<region>.amazonaws.com`) |
| **MinIO** | `http://minio.example.com:9000` (or `https://…` with TLS) |
| **DigitalOcean Spaces** | `https://nyc3.digitaloceanspaces.com` (region in subdomain) |
| **Cloudflare R2** | `https://<account_id>.r2.cloudflarestorage.com` |
| **Backblaze B2 (S3 API)** | `https://s3.<region>.backblazeb2.com` |
| **Wasabi** | `https://s3.<region>.wasabisys.com` |

## 1. Python library (default)

```python
import bucket_helper as bh

bh.credentials(config_path=None)                       # -> dict
bh.upload(local_path, cred, s3_address="", content_type=None)   # -> "s3://bucket/key"
bh.download(s3_address, local_path, cred)              # -> local_path
bh.exists(s3_address, cred)                            # -> bool
bh.list_prefix(prefix, cred, *, max_keys=1000)         # -> list[str]
bh.delete(s3_address, cred)                            # -> bool (idempotent)
bh.make_bucket(bucket, cred)                           # -> None (idempotent)
bh.strip_s3_path(s3_address, cred)                     # -> key str
bh.get_client_s3(cred)                                 # context manager -> boto3 client

with bh.remote_tempfile(cred, ext="", prefix="") as (s3_address, public_url):
    ...   # object at s3_address is deleted on exit, even on exception
```

The public API is fixed via `bucket_helper.__all__`. `upload` / `download` show
a byte-scaled `os_helper.progress_bar` (ETA, auto-quiet on a non-TTY) by wiring
boto3's transfer `Callback` — so moving a large object gives live feedback.

## 2. CLI — argparse (default) and click

- **argparse** `bucket-helper <sub> …` — ships with the base package, zero extra
  deps. Primary surface. See `cli-reference.md`.
- **click** `bucket-helper-click <sub> …` — install `bucket-helper[cli]`. Same
  subcommands and flag names; nicer `--help`, shell completion.

## 3. HTTP API — FastAPI (`bucket-helper[api]`)

```bash
pip install 'bucket-helper[api]'
uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000
# OpenAPI docs: http://localhost:8000/docs   (ReDoc at /redoc)
```

Endpoints:
- `GET  /health` — liveness probe → `{"status":"ok"}`.
- `POST /upload` — multipart `file` + `key` + `content_type` → JSON `{"s3_address": …}`.
- `POST /download` — `key` → streamed `FileResponse` (temp file cleaned up after).
- `POST /delete` — `key` → JSON `{"deleted": key}`.
- `POST /exists` — `key` → JSON `{"exists": true|false}`.
- `POST /list` — `prefix` + `max_keys` → JSON `{"keys": [...], "count": N}`.
- `POST /make-bucket` — `bucket` → JSON `{"bucket": …, "created": true}`.
- `POST /tempfile` — `ext` + `prefix` → JSON `{"s3_address": …, "public_url": …}` (uploads nothing).
- `POST /strip-path` — `address` → JSON `{"key": …}`.

**Credentials, two ways** (per-request wins over server default):
- **Server-side**: set `BUCKET_HELPER_CONFIG` in the process env; every request
  loads it via `credentials()`.
- **Per-request**: send `s3_access_key` / `s3_secret_key` / `s3_bucket` /
  `s3_https` (+ optional endpoint/region/prefix/path-style/verify-ssl) as form
  fields. A missing required credential fails fast with a 400.

Uploads spool to a temp file (never held whole in memory); temp dirs are cleaned
via `BackgroundTasks` after the response is streamed.

## Docker

The repo ships a `Dockerfile` that serves the API:

```bash
docker build -t bucket-helper .
docker run --rm -p 8000:8000 \
  -e BUCKET_HELPER_CONFIG=/config/s3_config.json \
  -v $PWD/s3_config.json:/config/s3_config.json:ro \
  bucket-helper
```
