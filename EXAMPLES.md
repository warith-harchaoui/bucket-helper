# Bucket Helper Examples

Practical recipes for `bucket-helper` against **AWS S3 and any
S3-compatible storage** (MinIO, Cloudflare R2, Backblaze B2, DigitalOcean
Spaces, Wasabi, …). Every snippet assumes:

```python
import bucket_helper as bh
import os_helper as osh
```

and that you have a configuration source (`settings.yaml`, `.env`, or
`S3_*` environment variables); see the README for the required keys
and the per-provider endpoint table.

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

---

## Setup

```bash
pip install --force-reinstall --no-cache-dir \
    bucket-helper
```

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
    # invoice already uploaded

# Bare key form (resolves under cred["s3_bucket"])
if bh.exists("invoices/2026/06.pdf", cred):
    print("same check, shorter")
    # same check, shorter

# List keys under a prefix (up to max_keys, default 1000)
for key in bh.list_prefix("invoices/2026/", cred, max_keys=200):
    print(key)
    # invoices/2026/01.pdf
    # invoices/2026/02.pdf
    # ...
```

For larger listings, drop down to the raw boto3 paginator via
`bh.get_client_s3(cred)`.

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

Per-provider endpoint values are listed in the
[README](README.md#endpoint-urls-for-common-s3-compatible-storage).

## Combining with sftp-helper / os-helper

Mirror an upload between AWS-style storage and an SFTP partner inbox:

```python
import os_helper as osh
import bucket_helper as bh
import sftp_helper as sftph

osh.verbosity(2)

s3_cred  = bh.credentials("path/to/settings.yaml")
sftp_cred = sftph.credentials("path/to/settings.yaml")

# Long-term archive on S3
s3_uri = bh.upload("report.pdf", s3_cred, "reports/2026-06.pdf")
# Mirror to SFTP partner
sftph.upload("report.pdf", sftp_cred, "/inbox/2026-06.pdf")

print(f"Archived at {s3_uri}; delivered to SFTP partner.")
# Archived at s3://my-bucket/reports/2026-06.pdf; delivered to SFTP partner.
```
