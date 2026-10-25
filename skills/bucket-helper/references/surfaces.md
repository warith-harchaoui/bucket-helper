# bucket-helper non-CLI surfaces

## 1. Library

```python
import bucket_helper as bh
```

Public API (`bucket_helper.__all__`): `credentials`, `get_client_s3`,
`upload`, `download`, `delete`, `exists`, `list_prefix`, `make_bucket`,
`remote_tempfile`, `strip_s3_path`.

```python
url = bh.upload("./report.pdf", "reports/2026/report.pdf")  # → public URL
for key in bh.list_prefix("reports/2026/"):
    ...
```

`credentials()` returns the resolved config dict and `get_client_s3()` the
underlying boto3 client — reach for the client only when you need an S3
operation this package does not wrap, and keep the credential resolution path
intact rather than building a client by hand.

Logging and file management route through `os_helper` — the suite convention.

## 2. CLI — click (core)

`bucket-helper`. See `cli-reference.md`.

## 3. HTTP API — FastAPI (`[api]`)

```bash
pip install 'bucket-helper[api]'
python -m bucket_helper.api         # 127.0.0.1:8000, OpenAPI docs at /docs
```

| Method | Route |
|---|---|
| GET | `/health` |
| POST | `/upload`, `/download`, `/exists`, `/list` |
| POST | `/delete`, `/make-bucket`, `/tempfile`, `/strip-path` |

The server reads credentials from its own environment — it does **not** accept
them per request, so an exposed port cannot be used to transfer someone else's
keys. Bind it to `127.0.0.1` and keep it there.

## 4. MCP — `fastapi-mcp` over the *same* app (`[mcp]`)

```bash
pip install 'bucket-helper[mcp]'
bucket-helper-mcp                   # same app, MCP mounted at /mcp
```

`bucket_helper.mcp` takes the FastAPI app from `bucket_helper.api` and mounts
`FastApiMCP` on it. Every MCP tool *is* an HTTP route, so the two surfaces
cannot drift and one process serves both doors.

Register it with Claude Code:

```bash
claude mcp add bucket-helper --transport http http://127.0.0.1:8000/mcp
```

**An agent holding these tools can write to, and delete from, the user's
storage.** The `delete` and `make-bucket` tools deserve an explicit
confirmation every time; so does an `upload` to a key that already exists.

## Where this sits in the suite

bucket-helper and `sftp-helper` are the suite's two transfer packages and the
only members whose job is to move data off the machine. They share the same
shape — `upload`, `download`, `exists`, `list`, `delete`, `tempfile`,
`strip-path` — so switching between object storage and a plain server is a
config change, not a rewrite.

Everything else in the suite stays local; these two exist because a pipeline
eventually has to publish its output somewhere the user chose.
