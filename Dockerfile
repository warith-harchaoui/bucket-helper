# syntax=docker/dockerfile:1.6
#
# bucket-helper — reproducible container image.
#
# Single-stage build: the base stage installs the package with the
# [api,mcp] extras so the container can serve the HTTP + MCP surfaces
# out of the box. No heavy system deps are needed — boto3 is a pure
# Python wheel — so the image stays lean.
#
# Build:
#   docker build -t bucket-helper .
#
# Run (HTTP + MCP on 0.0.0.0:8000):
#   docker run --rm -p 8000:8000 \
#     -e BUCKET_HELPER_CONFIG=/config/s3_config.json \
#     -v $PWD/s3_config.json:/config/s3_config.json:ro \
#     bucket-helper
#
# Run CLI one-shot:
#   docker run --rm -v $PWD:/data \
#     -e BUCKET_HELPER_CONFIG=/data/s3_config.json \
#     bucket-helper \
#     bucket-helper upload --config /data/s3_config.json --input /data/in.bin --key uploads/in.bin

# --- base -------------------------------------------------------------------
FROM python:3.11-slim AS base

# Minimal system deps: ca-certificates for HTTPS to S3 endpoints,
# tini for signal handling. No compilers — we install from wheels only.
RUN apt-get update && apt-get install --no-install-recommends -y \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Non-root runtime user; the app never needs root at runtime.
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# --- deps -------------------------------------------------------------------
# Copy the package first so pip picks up pyproject.toml before we invalidate
# the layer with source changes.
COPY --chown=app:app pyproject.toml README.md LICENSE ./
COPY --chown=app:app bucket_helper ./bucket_helper

# Install with API + MCP extras — the container's raison d'être is to
# serve the HTTP / MCP surfaces. CLI entry points come along for free.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir '.[api,mcp]'

# --- runtime ----------------------------------------------------------------
USER app
EXPOSE 8000
ENV PYTHONUNBUFFERED=1 \
    BUCKET_HELPER_HOST=0.0.0.0 \
    BUCKET_HELPER_PORT=8000

# tini reaps orphan children cleanly on SIGTERM.
ENTRYPOINT ["/usr/bin/tini", "--"]
# Default: serve FastAPI + MCP. Override for one-shot CLI usage.
CMD ["bucket-helper-mcp"]
