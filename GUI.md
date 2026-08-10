# GUI — Bucket Helper

> A design plan, not a CLI mirror. The CLI already handles "one blob at
> a time, one bucket at a time". A GUI must go further — otherwise why
> build one? This document lays out an ambitious, opinionated visual
> product for the *day-in-the-life-of-a-multi-bucket engineer*.

## North star

> **A single pane where every bucket (AWS, MinIO, R2, B2, Spaces,
> Wasabi) looks and behaves the same — and every mutation is undoable
> for 30 seconds.**

Object storage is inherently multi-region, multi-account, and
error-prone at the CLI (typo the bucket name → data goes to the wrong
place). The GUI's job is to make **cross-endpoint work uniform,
reversible, and observable** — not to reproduce `aws s3 cp` as a form.

## Three surfaces, one product

### 1. Unified Vault View *(primary surface)*

- Left rail: every configured credential (one entry per
  `settings.yaml`), grouped by *class* (AWS / MinIO / R2 / B2 / Spaces
  / Wasabi) and shown with the provider's own visual accent (color +
  logo) so a MinIO bucket never *looks* like an AWS bucket. Prevents
  the "wrong-account" foot-gun that costs money on AWS.
- Center: the bucket contents as a **columnar file browser** (path
  segments as breadcrumbs), with per-object **content sniffer**:
  drop-in previews for text / image / audio / JSON / CSV / Parquet
  without downloading the whole blob (uses HTTP Range on the FastAPI
  backend).
- Right rail: **per-object metadata panel** — size, ETag, last-modified,
  storage class, content-type, custom tags. Copyable `s3://…` URI and
  the `https://…` public URL (built from `cred['s3_https']`) with one
  click.
- Every mutation (upload / delete / rename) emits an **undo toast**
  with a 30-second window. Under the hood: uploads are staged behind a
  `remote_tempfile` key, deletes hold the object in a shadow prefix
  until the window expires. Zero foot-gun.

### 2. Ferry — cross-bucket + cross-provider copy

A two-panel view. Pick a source bucket on the left, a destination on
the right — the tool synthesizes a **byte-optimal transfer plan**:
either server-side copy (same provider, same region), or streamed
proxy through the FastAPI backend when the endpoints do not speak the
same S3 dialect. Shows:

- Predicted throughput based on last N transfers per endpoint pair.
- Delta view: which keys already exist at the destination (by ETag),
  which will be overwritten, which are new.
- Dry-run toggle: emits an rclone-equivalent script for CI.

Zero cost estimate is shown up front (egress + PUT + LIST for the
provider pair the user is targeting) — the numbers `mc` and `rclone`
hide.

### 3. Recipe Runner — replay pipelines

Every stage-and-share pipeline (upload → hand URL to worker → let
`remote_tempfile` clean up) is captured as a **replayable recipe**
(YAML). Drop a recipe into the runner:

- The runner shows each step as a live tile (waveform of a "state"
  spinner + last log line).
- On failure, the last-known-good state is preserved and the exact
  `s3://…` URI of the orphan blob is surfaced with a one-click
  cleanup button.

Recipes are byte-identical to what a `bucket-helper` CLI script would
produce — so anything you demo in the GUI runs headless in CI.

## Design principles

- **Provider identity is loud.** MinIO buckets are *green* and prefixed
  with a house icon; AWS is *orange*; R2 is *blue*. The one thing you
  never want is to accidentally delete a prod-AWS bucket thinking it
  was your dev MinIO. Color + shape + text — never color alone.
- **Everything reversible.** No confirm-dialog fatigue; instead the
  30-second undo toast + shadow-prefix for deletes. Same idea as Gmail
  send-undo, applied to object storage.
- **Content-type is a first-class citizen.** Every object shows what
  it *is*, not its extension. Bad content-type headers get a warning
  badge.
- **URLs are copyable everywhere.** Both `s3://bucket/key` and
  `https://…` — copy-paste is the number-one action in this workflow.
- **Endpoint agnostic.** MinIO, R2, B2, Spaces, Wasabi are first-class.
  No "AWS-only" features live in the primary surface; they show up
  under a `provider-specific` dropdown so a MinIO user never sees an
  AWS S3 Glacier button they cannot click.
- **Costed by default.** Egress + PUT + LIST prices are shown for every
  cross-provider action. AWS S3 traffic to the internet is the surprise
  bill nobody sees coming — the GUI shows it up front.

## What we deliberately don't do

- **No versioning / lifecycle configuration.** DVC and the provider
  consoles already do that. We stay in the CRUD + transfer lane.
- **No presigned-URL generator.** Boto3 already exposes it in two
  lines; we would just add a UI-first foot-gun.
- **No cloud lock-in.** Everything runs on the same local FastAPI
  server the container already ships. GUI is a thin JS client.

## Stack

- Front end: TypeScript + Svelte 5. No React — matches the `front-ui`
  companion skill's stack.
- Back end: the FastAPI app already exists (`bucket_helper.api`) and
  covers 100 % of the operations. GUI is a client only, plus a small
  helper endpoint for HTTP-Range-based content previews.
- Recipe format: YAML, versioned, human-diffable.

## Milestones

| Milestone | What ships | Why first |
| --- | --- | --- |
| M0 | Unified Vault View for one provider (AWS or MinIO). List + preview + copy-URI. | Prove the "one pane, uniform" claim before scaling to N providers. |
| M1 | Multi-provider credential rail. Provider-colored buckets. Upload + delete with 30-second undo. | Where the GUI starts to feel obviously safer than the CLI. |
| M2 | Ferry: cross-bucket same-provider server-side copy. | Delivers the most requested day-to-day action. |
| M3 | Ferry: cross-provider streaming copy through FastAPI. Cost estimator. | Where the GUI passes `mc` and `rclone` in transparency. |
| M4 | Recipe Runner: YAML pipelines, orphan-blob cleanup UI. | The "we can only do this in a GUI" moment — visual pipeline debugging. |

## Non-goals (recorded so we do not drift)

- Not a full S3 console.
- Not a hosted SaaS.
- Not a substitute for the CLI in CI (recipes emit CLI-equivalent
  YAML that CI can replay headless).

## Success metric

> A user who owns 4 accounts across AWS + MinIO + Cloudflare R2
> reconciles a "which of these buckets holds artifact X" investigation
> in one window, in under 60 seconds, without touching the terminal —
> and does not accidentally delete anything in the process.

If we ship that, we win.
