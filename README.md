# Bucket Helper

[🇫🇷](https://github.com/warith-harchaoui/bucket-helper/blob/main/LISEZMOI.md) · [🇬🇧](https://github.com/warith-harchaoui/bucket-helper/blob/main/README.md)

[![CI](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml/badge.svg)](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml) [![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://github.com/warith-harchaoui/bucket-helper/blob/main/LICENSE) [![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](#)

`Bucket Helper` belongs to a collection of libraries called `AI Helpers` developed for building Artificial Intelligence.

Utility functions for **AWS S3** and any **S3-compatible object storage** — MinIO, Backblaze B2 S3 API, DigitalOcean Spaces, Cloudflare R2, Wasabi, and friends. Built on [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). Same shape as [sftp-helper](https://github.com/warith-harchaoui/sftp-helper): a `credentials()` loader, the usual CRUD (`upload` / `download` / `delete` / `exists` / `list_prefix`), and a `remote_tempfile` context manager for stage-and-share flows.

[🌍 AI Helpers](https://harchaoui.org/warith/ai-helpers)

[![logo](https://raw.githubusercontent.com/warith-harchaoui/bucket-helper/main/assets/logo.png)](https://harchaoui.org/warith/ai-helpers)

## The Promise

**Remote by design.** `bucket-helper` exists to move data to and from *object
storage you choose* — AWS, or any S3-compatible endpoint you point it at
(including a MinIO instance on your own network). It is deliberately **not**
local-first and ships **no GUI**. For a remote reached over SFTP instead of
S3, use `sftp-helper`; for downloading media from a URL, use `youtube-helper`.

## Documentation

[💻 Documentation](https://harchaoui.org/warith/ai-helpers/docs/bucket-helper-doc/)

[🗺️ Landscape](https://github.com/warith-harchaoui/bucket-helper/blob/main/LANDSCAPE.md)

[📋 Examples](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXAMPLES.md)

[🎯 Triggers](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md)

## Features

- **CRUD** against AWS S3 or any S3-compatible endpoint: `upload`, `download`,
  `delete`, `exists`, `list_prefix`.
- **Works against any S3-compatible provider** — MinIO, Backblaze B2 S3 API,
  DigitalOcean Spaces, Cloudflare R2, Wasabi — by pointing the `endpoint_url`
  credential at it; no code changes per provider.
- **Credentials loader** (`credentials`) resolving JSON / YAML / environment
  variables / `.env`, in that fallback order.
- **`remote_tempfile`** context manager for stage-and-share flows — upload,
  hand back the object, auto-delete on block exit, no manual cleanup.
- **Three surfaces, one behavior** — Python library, argparse CLI, click CLI
  twin (`[cli]` extra), and FastAPI HTTP surface (`[api]` extra). See the
  [multi-surface section](#multi-surface-exposure).
- **Docker image** ships the HTTP server ready to run.

## Installation

**Prerequisites** — **Python 3.10–3.13** and **git**, cross-platform:

- 🍎 **macOS** ([Homebrew](https://brew.sh)): `brew install python git`
- 🐧 **Ubuntu/Debian**: `sudo apt update && sudo apt install -y python3 python3-pip git`
- 🪟 **Windows** (PowerShell): `winget install Python.Python.3.12 Git.Git`

We recommend using Python environments. Check this link if you're unfamiliar with setting one up: [🥸 Tech tips](https://harchaoui.org/warith/4ml/#install).

### From PyPI (recommended)

```bash
# Core library (credentials loader + CRUD + remote_tempfile)
pip install bucket-helper

# Optional surfaces
pip install "bucket-helper[cli]"       # click-based CLI twin
pip install "bucket-helper[api]"       # FastAPI HTTP surface
```

### From source (no PyPI)

```bash
# Core library
pip install bucket-helper

# Optional surfaces
pip install "bucket-helper[cli]"
pip install "bucket-helper[api]"
```

The argparse CLI is always available. The `[cli]` extra adds the click twin.

## Configuration

A ready-to-fill template is committed at [`settings.yaml.example`](https://github.com/warith-harchaoui/bucket-helper/blob/main/settings.yaml.example). Copy it to `settings.yaml` and edit in place — `settings.yaml` is gitignored so you cannot accidentally commit secrets:

```bash
cp settings.yaml.example settings.yaml
# then edit settings.yaml with your AWS / MinIO / R2 / B2 credentials
```

You may also write JSON instead of YAML, use a `.env`, or set environment variables — `bucket-helper` falls back in that order via `os_helper.get_config`. Required keys:

```json
{
  "s3_access_key": "AKIA...",
  "s3_secret_key": "...",
  "s3_bucket":     "my-bucket",
  "s3_https":      "https://my-bucket.s3.eu-west-3.amazonaws.com"
}
```

Optional keys:

| Key | Default | Notes |
|---|---|---|
| `s3_region` | `"us-east-1"` | AWS region; mostly cosmetic for MinIO / R2 |
| `s3_endpoint_url` | empty (= AWS S3) | Set this for S3-compatible backends — see table below |
| `s3_prefix` | empty | Default key prefix added by `upload(...)` when no destination is given |
| `s3_use_path_style` | `"false"` | Force path-style addressing (`endpoint/bucket/key` instead of `bucket.endpoint/key`). Typical for MinIO with custom domains. |
| `s3_verify_ssl` | `"true"` | Disable only for dev MinIO with self-signed certs |

## Endpoint URLs for common S3-compatible storage

Set `s3_endpoint_url` to:

| Provider | Endpoint |
|---|---|
| **AWS S3** | leave empty / unset |
| **MinIO** | `http://minio.example.com:9000` (or `https://...` with TLS) |
| **DigitalOcean Spaces** | `https://nyc3.digitaloceanspaces.com` (region in subdomain) |
| **Cloudflare R2** | `https://<account_id>.r2.cloudflarestorage.com` |
| **Backblaze B2 (S3 API)** | `https://s3.<region>.backblazeb2.com` |
| **Wasabi** | `https://s3.<region>.wasabisys.com` |

## Usage

For the full catalog of recipes (uploads / downloads / listings, S3-compatible endpoints — MinIO / R2 / B2 / Spaces / Wasabi, temporary remote keys with auto-cleanup, mirroring with sftp-helper), see [📋 EXAMPLES.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXAMPLES.md).

```python
import bucket_helper as bh

# Load creds — JSON / YAML / env / .env (auto-fallback in that order)
cred = bh.credentials("path/to/settings.yaml")

# Upload a local file
uri = bh.upload("local.txt", cred, "folder/uploaded.txt")
# uri == "s3://my-bucket/folder/uploaded.txt"

assert bh.exists(uri, cred)

# Download
bh.download(uri, "downloaded.txt", cred)

# List
for key in bh.list_prefix("folder/", cred):
    print(key)

# Delete
bh.delete(uri, cred)
```

## MinIO example

```python
cred = {
    "s3_access_key":      "minioadmin",
    "s3_secret_key":      "minioadmin",
    "s3_bucket":          "uploads",
    "s3_https":           "http://minio.example.com:9000/uploads",
    "s3_endpoint_url":    "http://minio.example.com:9000",
    "s3_use_path_style":  "true",
    "s3_region":          "us-east-1",  # MinIO accepts any region string
}

bh.make_bucket("uploads", cred)
bh.upload("file.bin", cred, "file.bin")
```

## Stage-and-share with `remote_tempfile`

Drop a generated file at a unique random key, hand the public URL to a
downstream worker / webhook, and the object is deleted on block exit
(even if the body raises):

```python
import bucket_helper as bh
import requests

cred = bh.credentials("path/to/settings.yaml")

with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    # Hand the URL to something that fetches it once.
    requests.post("https://hook.example.com/process", json={"input_url": public_url}).raise_for_status()
# Object is gone here, no manual cleanup.
```

## Multi-surface exposure

Every public function in the library is also exposed as:

- **argparse CLI** — `bucket-helper <subcommand>` (installed by default).
- **click CLI** — `bucket-helper-click <subcommand>` (install `[cli]` extra).
- **FastAPI HTTP** — `uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000` (install `[api]` extra).
- **MCP** — `bucket-helper-mcp` exposes the same HTTP surface as MCP tools for
  any MCP-aware agent host (install `[mcp]` extra).

Both CLIs share the same subcommand names and flags — pick your favourite.

The exhaustive catalogue of what triggers the toolkit — natural-language
phrasings, commands, functions, address cues, and explicit SKIP rules — lives in
[TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md).

## CLI examples

```bash
# argparse CLI (always available)
bucket-helper upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config settings.yaml --key folder/uploaded.txt
bucket-helper download    --config settings.yaml --key folder/uploaded.txt --output back.txt
bucket-helper list        --config settings.yaml --prefix folder/
bucket-helper delete      --config settings.yaml --key folder/uploaded.txt
bucket-helper make-bucket --config settings.yaml --bucket new-bucket
bucket-helper tempfile    --config settings.yaml --ext json --prefix runs
bucket-helper strip-path  --config settings.yaml --address s3://my-bucket/path/to/obj

# click CLI — same verbs, same flags
bucket-helper-click upload --config settings.yaml --input local.txt --key folder/uploaded.txt
```

## HTTP server

```bash
# Serve HTTP (default credentials picked up from BUCKET_HELPER_CONFIG)
BUCKET_HELPER_CONFIG=$PWD/settings.yaml uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000
# → Swagger UI at http://localhost:8000/docs
```

Per-request credentials can also be sent as multipart form fields
(`s3_access_key` / `s3_secret_key` / `s3_bucket` / `s3_https` / …).

## Docker

```bash
docker build -t bucket-helper .
docker run --rm -p 8000:8000 \
  -e BUCKET_HELPER_CONFIG=/config/settings.yaml \
  -v $PWD/settings.yaml:/config/settings.yaml:ro \
  bucket-helper
```

See also: [TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md) (what invokes the toolkit) and
[GUI.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/GUI.md) (visual product design plan — no GUI ships; bucket-helper is remote object-storage plumbing).

## Author

 - [Warith HARCHAOUI](https://linkedin.com/in/warith-harchaoui)

## Acknowledgements

Special thanks to [Mohamed Chelali](https://mchelali.github.io) and [Bachir Zerroug](https://www.linkedin.com/in/bachirzerroug) for fruitful discussions.

## License

This project is licensed under the BSD-3-Clause License — see the [LICENSE](https://github.com/warith-harchaoui/bucket-helper/blob/main/LICENSE) file for details.
