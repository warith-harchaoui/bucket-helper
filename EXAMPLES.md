# Bucket Helper Examples

Practical recipes for `bucket-helper` against **AWS S3 and any
S3-compatible storage** (MinIO, Cloudflare R2, Backblaze B2, DigitalOcean
Spaces, Wasabi, …). Every snippet below starts from the imports and the
credentials source laid out in [Setup](#setup), so you can jump straight
to the section you need.

Every call here reaches a bucket, which means every call needs
credentials. Nothing below was run against real storage: the Python
snippets were checked against the signatures in `bucket_helper/main.py`,
so no output is shown for them. The captured output you do see is in
[Command line](#command-line), where `--help` and `strip-path` answer
without opening a connection.

---

## Table of Contents

1. [Setup](#setup)
2. [Load credentials](#load-credentials)
3. [Upload / download / delete](#upload--download--delete)
4. [Existence + listing](#existence--listing)
5. [Buckets: create on demand](#buckets-create-on-demand)
6. [Temporary remote keys (auto-cleanup)](#temporary-remote-keys-auto-cleanup)
7. [S3-compatible endpoints (MinIO / R2 / B2 / Spaces / Wasabi)](#s3-compatible-endpoints-minio--r2--b2--spaces--wasabi)
8. [Combining with sftp-helper / os-helper](#combining-with-sftp-helper--os-helper)
9. [Command line](#command-line)
10. [Troubleshooting](#troubleshooting)

---

## Setup

```bash
pip install --force-reinstall --no-cache-dir \
    bucket-helper
```

The CLI ships with that core install. The HTTP surface and the MCP server
are extras:

```bash
pip install "bucket-helper[api]"       # FastAPI HTTP surface
pip install "bucket-helper[mcp]"       # MCP server (pulls [api] in)
```

Every Python snippet below assumes these two imports:

```python
import bucket_helper as bh
import os_helper as osh
```

…and a configuration source holding at least `s3_access_key`,
`s3_secret_key`, `s3_bucket` and `s3_https` — a `settings.yaml`, a
`.env`, or the matching environment variables. See the README for the
full key list and the per-provider endpoint table.

Underneath, `bucket-helper` is a thin layer on top of
[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).
Anything that speaks the AWS S3 API works; set `s3_endpoint_url` for
non-AWS backends.

## Load credentials

```python
# YAML / JSON file (preferred for ops)
cred = bh.credentials("path/to/settings.yaml")

# Fall back to .env / S3_* environment variables
cred = bh.credentials()
```

Optional keys (`s3_region`, `s3_endpoint_url`, `s3_prefix`,
`s3_use_path_style`, `s3_verify_ssl`) are picked up best-effort from the
same sources; see the README endpoint table for the per-provider
values.

## Upload / download / delete

```python
# Upload: destination key under default bucket
uri = bh.upload("invoice.pdf", cred, "invoices/2026/06.pdf")
# uri == "s3://my-bucket/invoices/2026/06.pdf"

# Upload with no destination: random unique name under cred["s3_prefix"]
uri = bh.upload("snapshot.bin", cred)
# uri == "s3://my-bucket/<random_hex>.bin"

# Upload with explicit MIME type (default = boto3 / server-side guess)
bh.upload("page.html", cred, "site/index.html", content_type="text/html")

# Download
bh.download("s3://my-bucket/invoices/2026/06.pdf", "06.pdf", cred)

# Delete: idempotent (always returns True if the object is gone after the call)
bh.delete("s3://my-bucket/invoices/2026/06.pdf", cred)
```

You can mix-and-match `"s3://bucket/key"` URIs and plain `"key"`
addresses; bare keys resolve under `cred["s3_bucket"]`.

## Existence + listing

```python
if bh.exists("s3://my-bucket/invoices/2026/06.pdf", cred):
    print("invoice already uploaded")

# Bare key form (resolves under cred["s3_bucket"])
if bh.exists("invoices/2026/06.pdf", cred):
    print("same check, shorter")

# List keys under a prefix (up to max_keys, default 1000).
# Keys come back in S3's own lexicographic order, un-sorted client-side.
for key in bh.list_prefix("invoices/2026/", cred, max_keys=200):
    print(key)
```

`list_prefix` stops at `max_keys` and cannot tell you whether it stopped
early — 200 keys looks the same whether the prefix holds exactly 200
objects or twenty thousand. When a program (rather than a human) acts on
the list, ask for the extra bit:

```python
keys, truncated = bh.list_prefix_page("invoices/2026/", cred, max_keys=200)
if truncated:
    print("more than 200 invoices under that prefix; raise max_keys")
```

It asks S3 for one key beyond the cap and reports whether it arrived, so
the extra cost is a single key.

For larger listings still, drop down to the raw boto3 paginator via
`bh.get_client_s3(cred)`, which is a context manager:

```python
with bh.get_client_s3(cred) as s3:
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cred["s3_bucket"], Prefix="invoices/"):
        for obj in page.get("Contents") or []:
            print(obj["Key"], obj["Size"])
```

## Buckets: create on demand

`make_bucket` is idempotent and honors `cred["s3_region"]` (no
LocationConstraint for `us-east-1`, per AWS quirk):

```python
bh.make_bucket("ephemeral-uploads", cred)
```

## Temporary remote keys (auto-cleanup)

`remote_tempfile` reserves a unique random key in the default bucket
and deletes the object on block exit, even on exception. Useful for
stage-and-share flows (upload, hand the public URL to a downstream
consumer, clean up):

```python
import requests

cred = bh.credentials("path/to/settings.yaml")

with bh.remote_tempfile(cred, ext="json", prefix="runs") as (s3_addr, public_url):
    bh.upload("payload.json", cred, s3_addr, content_type="application/json")
    requests.post(
        "https://hook.example.com/process",
        json={"input_url": public_url},
    ).raise_for_status()
# The object is gone here, no manual cleanup.
```

The `public_url` is built from `cred["s3_https"]`; set that to the CDN
or the bucket's public hostname depending on your topology.

## S3-compatible endpoints (MinIO / R2 / B2 / Spaces / Wasabi)

Set `s3_endpoint_url` on the credentials dict and (for MinIO especially)
`s3_use_path_style=true`:

```python
cred = {
    "s3_access_key": "minioadmin",
    "s3_secret_key": "minioadmin",
    "s3_bucket": "uploads",
    "s3_https": "http://minio.example.com:9000/uploads",
    "s3_endpoint_url": "http://minio.example.com:9000",
    "s3_use_path_style": "true",
    "s3_region": "us-east-1",  # MinIO accepts any region string
}

bh.make_bucket("uploads", cred)
bh.upload("file.bin", cred, "file.bin")
```

Per-provider endpoint values are listed in the
[README](README.md#endpoint-urls-for-common-s3-compatible-storage).

## Combining with sftp-helper / os-helper

Mirror an upload between AWS-style storage and an SFTP partner inbox.
`sftp-helper` is a separate package (`pip install sftp-helper`); one
`settings.yaml` can carry both credential sets, because each loader only
reads the keys it declares:

```python
import os_helper as osh
import bucket_helper as bh
import sftp_helper as sftph

# One knob for the whole suite's logging; both helpers route through it.
osh.verbosity(2)

s3_cred = bh.credentials("path/to/settings.yaml")
sftp_cred = sftph.credentials("path/to/settings.yaml")

# Long-term archive on S3
s3_uri = bh.upload("report.pdf", s3_cred, "reports/2026-06.pdf")
# Mirror to the SFTP partner
sftph.upload("report.pdf", sftp_cred, "/inbox/2026-06.pdf")

print(f"Archived at {s3_uri}; delivered to SFTP partner.")
```

## Command line

One command line, `bucket-helper`, built with click. Eight verbs, the
same eight the HTTP surface exposes:

```console
$ bucket-helper --help
Usage: bucket-helper [OPTIONS] COMMAND [ARGS]...

  Bucket Helper — S3-compatible object storage from the shell.

Options:
  -V, --version  Show the version and exit.
  -h, --help     Show this message and exit.

Commands:
  delete       Delete an S3 object (idempotent).
  download     Download an S3 object to a local path.
  exists       Return exit code 0 if the object exists, 1 otherwise.
  list         List keys under a prefix in the default bucket.
  make-bucket  Create a bucket (no-op if it already exists).
  strip-path   Extract the key part of an 's3://bucket/key' address.
  tempfile     Emit a unique random key + public URL (JSON).
  upload       Upload a local file to S3.
```

Every verb takes `--config`, pointing at a `settings.yaml` (or a folder
holding one); omit it to fall back to `.env` and the environment:

```bash
bucket-helper upload      --config settings.yaml --input local.txt --key folder/uploaded.txt
bucket-helper exists      --config settings.yaml --key folder/uploaded.txt
bucket-helper download    --config settings.yaml --key folder/uploaded.txt --output back.txt
bucket-helper list        --config settings.yaml --prefix folder/ --max-keys 200
bucket-helper delete      --config settings.yaml --key folder/uploaded.txt
bucket-helper make-bucket --config settings.yaml --bucket new-bucket
bucket-helper tempfile    --config settings.yaml --ext json --prefix runs
bucket-helper strip-path  --config settings.yaml --address s3://my-bucket/path/to/obj
```

`strip-path` is pure string work, so it is the one verb that answers
without touching the network — here with the credentials coming from the
environment rather than a file, hence no `--config`:

```console
$ bucket-helper strip-path --address s3://my-bucket/path/to/obj
path/to/obj
```

Two behaviours worth knowing before you put these in a script:

- `exists` prints `true` / `false` **and** exits 1 when the object is
  absent, so `if bucket-helper exists …; then` works directly.
- `list` caps at `--max-keys` (1000 by default) and, when it hits the
  cap, prints a warning to **stderr** while the keys stay on stdout —
  a pipe is unaffected, and an `xargs` over the output no longer
  silently misses objects.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `RuntimeError: Missing required keys for 'S3' configuration in files, .env files, or environment variables.` | no source resolved all four required keys — the message does not say which one is missing | point `--config` at the file, or export `s3_access_key`, `s3_secret_key`, `s3_bucket` and `s3_https` |
| Requests to a MinIO behind a custom domain fail to authenticate | the default addressing is virtual-hosted (`bucket.endpoint/key`); that deployment wants `endpoint/bucket/key` | set `s3_use_path_style: "true"` |
| TLS verification fails against a development MinIO | self-signed certificate | set `s3_verify_ssl: "false"` — for a host you control, and nowhere else |
| `ModuleNotFoundError: No module named 'bucket_helper.cli_argparse'` | a `bucket-helper` console script left behind by a pre-`v1.3.0` install, pointing at a module that no longer exists | reinstall: `pip install --force-reinstall bucket-helper` |
| A listing returns exactly `--max-keys` keys and you cannot tell if that was all | `list_prefix` does not report its own cap | use `list_prefix_page`, or read the stderr warning `bucket-helper list` prints |
