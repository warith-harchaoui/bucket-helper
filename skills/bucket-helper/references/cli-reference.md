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
bucket-helper upload   LOCAL_PATH REMOTE_KEY [--bucket NAME] [--config PATH]
bucket-helper download REMOTE_KEY LOCAL_PATH [--bucket NAME] [--config PATH]
```

`upload` prints the public URL built from `s3_https` — that URL is the result
worth reporting, not the local path. An upload to an existing key **overwrites
it**; run `exists` first when that is a possibility.

## Inspection

```bash
bucket-helper exists REMOTE_KEY [--bucket NAME]
bucket-helper list   PREFIX     [--bucket NAME] [--limit N]
```

`list` matches by **string prefix**, not by directory: `a/b` also matches
`a/bc/…`. Include the trailing slash when you mean a folder.

## Mutation — confirm with the user first

```bash
bucket-helper delete      REMOTE_KEY [--bucket NAME]
bucket-helper make-bucket NAME
```

Both change storage the user is paying for and neither is undoable. Name the
bucket and the exact key back to them before calling either.

## Utilities

```bash
bucket-helper tempfile   [--suffix .wav] [--bucket NAME]   # a fresh remote key
bucket-helper strip-path s3://bucket/some/key.ext          # → bucket, key
```

`tempfile` mints a collision-free key for pipeline intermediates.
`strip-path` splits an `s3://` URL correctly, including keys containing
slashes — use it instead of string surgery.

## Output contract

- `upload` prints the public object URL.
- `download` prints the local path written.
- `exists` prints `true` / `false` and exits `0` either way; a genuine failure
  (bad credentials, unreachable endpoint) exits non-zero.
- `list` prints one key per line.
- Failures are logged through `os_helper` and exit non-zero; a partial
  download is removed rather than left behind.

## When a call fails

1. **403 / SignatureDoesNotMatch** — credentials resolved, but to the wrong
   values, or the key lacks permission on that bucket. Check *which* config
   won the precedence order before changing anything.
2. **404 / NoSuchKey** — confirm with `exists`; remember prefixes are
   case-sensitive and have no implicit directories.
3. **Endpoint errors on a non-AWS provider** — MinIO, R2, B2 and Scaleway each
   need their own endpoint URL in the config; the default is AWS.
