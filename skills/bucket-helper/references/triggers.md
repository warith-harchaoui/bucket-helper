# bucket-helper skill — exhaustive trigger catalogue

Auditable superset of the `description:` TRIGGER clause in `SKILL.md` (the
description is what a host model sees before loading; this file is the
human-reviewable full list). Keep the two in sync, and mirror the repo-root
`TRIGGERS.md`.

`bucket-helper` moves files to and from **remote, S3-shaped object storage**.
It is remote by design: there is no local-first mode and no GUI.

## Fire (positive triggers)

**Upload**
- "upload / put / push this file to S3 / my bucket / the bucket"
- "store this on MinIO / R2 / B2 / Spaces / Wasabi"
- "save this to s3://bucket/key", "write this object", "stage this file remotely"
- "upload it and give me back the URI"

**Download**
- "download s3://…", "fetch this key / object to a local file"
- "pull this down from the bucket", "get this object locally"

**Exists**
- "does this key / object exist in the bucket", "is s3://… there"
- "check if this object is already uploaded"

**List**
- "list the keys / objects under this prefix", "what's in my bucket / this folder"
- "show me everything under uploads/", "enumerate the objects"

**Delete**
- "delete / remove / drop this object / key", "clean up s3://…"
- "get rid of this file on the bucket"

**Make bucket**
- "create / make a bucket", "provision a new bucket"

**Stage-and-share (remote_tempfile)**
- "give me a throwaway remote key + public URL that cleans itself up"
- "stage this and hand me a shareable URL", "upload temporarily then auto-delete"
- "I need a temp s3 key for a one-shot handoff to a worker / webhook"

**Strip path**
- "strip the bucket off this s3:// URI", "get the key part of s3://bucket/key"
- "normalise this address to just the key"

**Credentials**
- "load my s3_config.json / s3_config.yaml", "use these S3 credentials"
- "read the bucket creds from env / .env"

**Explicit command / function mentions**
- `bucket-helper`, `bucket-helper-click`, `bucket-helper-mcp`
- subcommands `upload download delete exists list make-bucket tempfile strip-path`
- functions `credentials upload download delete exists list_prefix make_bucket
  remote_tempfile strip_s3_path get_client_s3`

**Address / endpoint cues** (with a read/write intent)
- an `s3://bucket/key` URI
- an S3 endpoint: `*.amazonaws.com`, `*.r2.cloudflarestorage.com`,
  `*.backblazeb2.com`, `*.digitaloceanspaces.com`, `*.wasabisys.com`, a MinIO
  `:9000` endpoint
- an `s3_config.json` / `s3_config.yaml` file in play

**Surfaces**
- "run the bucket-helper API / HTTP server", "expose these as HTTP / MCP tools"
- "how do I install / run bucket-helper"

## Do NOT fire (SKIP)

- **Non-S3-shaped storage** → not this skill:
  - Google Cloud Storage *native* API, Azure Blob Storage *native* API (use
    their SDKs; only their S3-compatibility gateways qualify).
  - Plain local filesystem operations (`cp`, `mv`, `os`, `shutil`, `pathlib`).
  - FTP / SFTP → use **sftp-helper** (bucket-helper mirrors its shape but talks S3).
- **Out-of-scope S3 features** → boto3 / provider console directly:
  - Presigned URL generation, bucket policies, IAM, ACLs.
  - Lifecycle rules, versioning, replication, CORS, encryption config, storage
    class transitions (Glacier, etc.).
- **Directory-tree sync / mirroring** ("sync this folder to the bucket",
  "mirror", "rsync to S3") → use `rclone`, `aws s3 sync`, or `mc mirror`.
  bucket-helper moves objects one at a time, not whole trees.
- **Data versioning** (DVC, lakeFS, git-lfs-over-S3) → not this skill.
- **File-*content* work** (parse / transform / transcode / compress the bytes)
  → a content-specific helper. bucket-helper moves the file; it does not read
  or rewrite its contents.
- **Anything asking for a GUI / local-first mode** → does not exist here, by
  design; do not promise one.

## Enforcement checklist

A trigger is "enforced" when (1) it is represented in `SKILL.md`'s `description`
TRIGGER clause so the host sees it pre-load; (2) the SKIP clause is present so
the skill does not over-fire (sftp-helper, sync tools, presigned URLs, non-S3
clouds); (3) this catalogue lists the positive and negative buckets so a human
can audit coverage against the description.
