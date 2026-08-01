# Bucket Helper

[🇫🇷](https://github.com/warith-harchaoui/bucket-helper/blob/main/LISEZMOI.md) · [🇬🇧](https://github.com/warith-harchaoui/bucket-helper/blob/main/README.md)

[![CI](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml/badge.svg)](https://github.com/warith-harchaoui/bucket-helper/actions/workflows/ci.yml) [![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://github.com/warith-harchaoui/bucket-helper/blob/main/LICENSE) [![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](#)

`Bucket Helper` belongs to a collection of libraries called `AI Helpers` developed for building Artificial Intelligence.

Utility functions for **AWS S3** and any **S3-compatible object storage** — MinIO, Backblaze B2 S3 API, DigitalOcean Spaces, Cloudflare R2, Wasabi, and friends. Built on [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). Same shape as [sftp-helper](https://github.com/warith-harchaoui/sftp-helper): a `credentials()` loader, the usual CRUD (`upload` / `download` / `delete` / `exists` / `list_prefix`), and a `remote_tempfile` context manager for stage-and-share flows.

[🌍 AI Helpers](https://harchaoui.org/warith/ai-helpers)

[![logo](https://raw.githubusercontent.com/warith-harchaoui/bucket-helper/main/assets/logo.png)](https://harchaoui.org/warith/ai-helpers)

## Documentation

[💻 Documentation](https://harchaoui.org/warith/ai-helpers/docs/bucket-helper-doc/)

[🗺️ Landscape](https://github.com/warith-harchaoui/bucket-helper/blob/main/LANDSCAPE.md)

[📋 Examples](https://github.com/warith-harchaoui/bucket-helper/blob/main/EXAMPLES.md)

[🎯 Triggers](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md) · [🧩 Agent skill](https://github.com/warith-harchaoui/bucket-helper/blob/main/skills/README.md)

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
pip install "git+https://github.com/warith-harchaoui/bucket-helper.git@v0.4.0"

# Optional surfaces
pip install "bucket-helper[cli] @ git+https://github.com/warith-harchaoui/bucket-helper.git@v0.4.0"
pip install "bucket-helper[api] @ git+https://github.com/warith-harchaoui/bucket-helper.git@v0.4.0"
```

The argparse CLI is always available. The `[cli]` extra adds the click twin.

## Configuration

A ready-to-fill template is committed at [`s3_config.json.example`](https://github.com/warith-harchaoui/bucket-helper/blob/main/s3_config.json.example). Copy it to `s3_config.json` and edit in place — real `*config.json` files are gitignored so you cannot accidentally commit secrets:

```bash
cp s3_config.json.example s3_config.json
# then edit s3_config.json with your AWS / MinIO / R2 / B2 credentials
```

You may also write a `s3_config.yaml`, use a `.env`, or set environment variables — `bucket-helper` falls back in that order via `os_helper.get_config`. Required keys:

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
cred = bh.credentials("path/to/s3_config.json")

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

cred = bh.credentials("path/to/s3_config.json")

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

Both CLIs share the same subcommand names and flags — pick your favourite.

## Agent skill (Claude / OpenCode)

`bucket-helper` ships as a discoverable **Claude Skill** *and* **OpenCode skill**
under [`skills/bucket-helper/`](https://github.com/warith-harchaoui/bucket-helper/blob/main/skills/bucket-helper/SKILL.md),
so an AI agent can run object-storage operations for you without you opening a
terminal. Install it by symlinking:

```bash
ln -sfn "$PWD/skills/bucket-helper" ~/.claude/skills/bucket-helper     # Claude Code / Desktop
ln -sfn "$PWD/skills/bucket-helper" ~/.opencode/skills/bucket-helper   # OpenCode
```

The exhaustive catalogue of what triggers the toolkit — natural-language
phrasings, commands, functions, address cues, and explicit SKIP rules — lives in
[TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md)
(mirrored in the skill's `references/triggers.md`). See
[skills/README.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/skills/README.md)
for install details.

## CLI examples

```bash
# argparse CLI (always available)
bucket-helper upload      --config s3_config.json --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config s3_config.json --key folder/uploaded.txt
bucket-helper download    --config s3_config.json --key folder/uploaded.txt --output back.txt
bucket-helper list        --config s3_config.json --prefix folder/
bucket-helper delete      --config s3_config.json --key folder/uploaded.txt
bucket-helper make-bucket --config s3_config.json --bucket new-bucket
bucket-helper tempfile    --config s3_config.json --ext json --prefix runs
bucket-helper strip-path  --config s3_config.json --address s3://my-bucket/path/to/obj

# click CLI — same verbs, same flags
bucket-helper-click upload --config s3_config.json --input local.txt --key folder/uploaded.txt
```

## HTTP server

```bash
# Serve HTTP (default credentials picked up from BUCKET_HELPER_CONFIG)
BUCKET_HELPER_CONFIG=$PWD/s3_config.json uvicorn bucket_helper.api:app --host 0.0.0.0 --port 8000
# → Swagger UI at http://localhost:8000/docs
```

Per-request credentials can also be sent as multipart form fields
(`s3_access_key` / `s3_secret_key` / `s3_bucket` / `s3_https` / …).

## Docker

```bash
docker build -t bucket-helper .
docker run --rm -p 8000:8000 \
  -e BUCKET_HELPER_CONFIG=/config/s3_config.json \
  -v $PWD/s3_config.json:/config/s3_config.json:ro \
  bucket-helper
```

See also: [TRIGGERS.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/TRIGGERS.md) (what invokes the toolkit),
[skills/README.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/skills/README.md) (agent skill install) and
[GUI.md](https://github.com/warith-harchaoui/bucket-helper/blob/main/GUI.md) (visual product design plan — no GUI ships; bucket-helper is remote object-storage plumbing).

## Author

 - [Warith HARCHAOUI](https://linkedin.com/in/warith-harchaoui)

## Acknowledgements

Special thanks to [Mohamed Chelali](https://mchelali.github.io) and [Bachir Zerroug](https://www.linkedin.com/in/bachirzerroug) for fruitful discussions.

## License

This project is licensed under the BSD-3-Clause License — see the [LICENSE](LICENSE) file for details.
