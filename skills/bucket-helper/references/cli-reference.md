# bucket-helper CLI reference

One CLI, `bucket-helper`, built with click and shipped with the core package,
over the same operations the library and the HTTP surface expose, with the
same subcommands and flags.

## Configuration

Credentials resolve through `os_helper.get_config`, in precedence order:
a JSON / YAML config file, a `.env`, then environment variables.

| Key | Meaning |
|---|---|
| `s3_access_key` | access key ID |
| `s3_secret_key` | secret access key |
| `s3_bucket` | default bucket |
| `s3_https` | base public URL used to build object URLs |

Start from the repo's `settings.yaml.example`. Point any command at a
different config with `--config PATH`.

**Never echo a secret.** If a command needs a key, it reads it; it does not
print it, and neither should you.

## Transfer

```bash
bucket-helper upload   --input LOCAL_PATH [--key REMOTE_KEY] [--content-type TYPE] [--config PATH]
bucket-helper download --key REMOTE_KEY --output LOCAL_PATH [--config PATH]
```

Every flag is named: no subcommand takes a positional argument. `--key`
accepts a bare key (resolved against `s3_bucket`) or a full `s3://bucket/key`
URI; the bucket is chosen that way, there is no `--bucket` flag on these
commands.

`upload` prints the `s3://bucket/key` URI of the object. Without `--key` it
picks a random name under `s3_prefix`, keeping the file's extension. An upload
to an existing key **overwrites it**; run `exists` first when that is a
possibility. For a public `https://` URL, use `tempfile`, the one command that
builds one from `s3_https`.

## Inspection

```bash
bucket-helper exists --key REMOTE_KEY [--config PATH]
bucket-helper list   --prefix PREFIX [--max-keys N] [--config PATH]
```

`list` matches by **string prefix**, not by directory: `a/b` also matches
`a/bc/…`. Include the trailing slash when you mean a folder.

## Mutation — confirm with the user first

```bash
bucket-helper delete      --key REMOTE_KEY [--config PATH]
bucket-helper make-bucket --bucket NAME [--config PATH]
```

Both change storage the user is paying for and neither is undoable. Name the
bucket and the exact key back to them before calling either.

## Utilities

```bash
bucket-helper tempfile   [--ext wav] [--prefix runs] [--config PATH]   # a fresh remote key
bucket-helper strip-path --address s3://bucket/some/key.ext [--config PATH]   # → some/key.ext
```

`tempfile` mints a collision-free key for pipeline intermediates and prints
it as JSON, `{"s3_address": ..., "public_url": ...}`, the URL built from
`s3_https`. It uploads nothing. `strip-path` prints the key part of an
`s3://` URL, slashes inside the key included — use it instead of string
surgery.

## Output contract

- `upload` prints the `s3://bucket/key` URI of the object.
- `download` prints the local path written.
- `exists` prints `true` and exits `0`, or prints `false` and exits `1`, so it
  works in a shell `if`. A genuine failure (bad credentials, unreachable
  endpoint) prints one `Error: ...` line and exits `1` too: read the output,
  not only the exit code.
- `list` prints one key per line, capped at `--max-keys` (1000 by default),
  with a warning on stderr when more keys exist.
- `delete` and `make-bucket` print nothing; both are no-ops when the object is
  already gone or the bucket already exists.
- `tempfile` prints a JSON object; `strip-path` prints the key.
- Failures are logged through `os_helper` and exit non-zero; a partial
  download is removed rather than left behind.

## When a call fails

1. **403 / SignatureDoesNotMatch** — credentials resolved, but to the wrong
   values, or the key lacks permission on that bucket. Check *which* config
   won the precedence order before changing anything.
2. **404 / NoSuchKey** — confirm with `exists`; remember prefixes are
   case-sensitive and have no implicit directories.
3. **Endpoint errors on a non-AWS provider** — MinIO, R2, B2 and Scaleway each
   need their own `s3_endpoint_url` in the config (plus `s3_use_path_style:
   "true"` for most MinIO setups); empty means AWS.
