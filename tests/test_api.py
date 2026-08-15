"""
Smoke tests for the FastAPI HTTP surface.

Only exercises endpoints that do not require live S3 credentials
(``/health``, plus OpenAPI schema introspection to catch endpoint-name
drift). Heavier round-trip tests belong to the ``integration`` suite
where a real (or moto-mocked) S3 endpoint is wired end-to-end through
the API.

Usage Example
-------------
>>> #   pytest tests/test_api.py

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import pytest

# FastAPI is in the ``[api]`` optional extra — skip cleanly otherwise.
fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """Yield a TestClient bound to the bucket-helper FastAPI app."""
    from bucket_helper.api import app

    with TestClient(app) as c:
        yield c


def test_health_returns_ok(client):
    """``/health`` should return 200 + ``{"status": "ok"}``."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_lists_expected_endpoints(client):
    """The OpenAPI spec should list every expected route path."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = {
        "/health",
        "/upload",
        "/download",
        "/delete",
        "/exists",
        "/list",
        "/make-bucket",
        "/tempfile",
        "/strip-path",
    }
    assert expected.issubset(set(paths.keys()))


def test_openapi_version_matches_package_metadata(client):
    """The OpenAPI ``info.version`` should track the installed package version.

    The app resolves its version from ``importlib.metadata`` rather than a
    hardcoded literal, so this guards against the old drift (the spec was once
    frozen at ``0.2.2`` while the package moved on).
    """
    from importlib.metadata import version

    r = client.get("/openapi.json")
    assert r.status_code == 200
    # In an editable/installed test env the package metadata is available; the
    # OpenAPI spec must echo exactly that string.
    assert r.json()["info"]["version"] == version("bucket-helper")


def test_docs_endpoint_is_served(client):
    """``/docs`` should serve the Swagger UI landing HTML."""
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower() or "openapi" in r.text.lower()


def test_missing_cred_returns_400(client):
    """A mutation without any credentials should fail fast with a 400."""
    # We hit /exists with a bare key but no credentials at all — the
    # server has no BUCKET_HELPER_CONFIG default in the test env, so
    # this must be a 400 (missing credential), not a 500 (crash).
    r = client.post("/exists", data={"key": "some/key"})
    # Some FastAPI versions surface HTTPException as 400; the important
    # bit is that we do not 500 on a missing credential.
    assert r.status_code == 400
    assert "credential" in r.json().get("detail", "").lower()


_FAKE_CRED = {
    "s3_access_key": "AKIAFAKEFAKEFAKEFAKE",
    "s3_secret_key": "fakesecretfakesecretfakesecretfakesecret",
    "s3_bucket": "test-bucket",
    "s3_https": "https://test-bucket.s3.amazonaws.com",
    "s3_region": "us-east-1",
}


def test_malformed_s3_address_returns_400_not_500(client):
    """A malformed ``s3://`` URI (empty bucket) is a client-input error: 400.

    ``_split_s3_address`` raises ``ValueError`` for this — previously
    uncaught, it fell through to FastAPI's generic 500 handler.
    """
    r = client.post("/strip-path", data={"address": "s3:///no-bucket-here", **_FAKE_CRED})
    assert r.status_code == 400


def test_s3_client_error_returns_502_not_500(client):
    """An upstream S3 failure (e.g. a bucket that doesn't exist) maps to 502.

    ``exists()`` only swallows 404/NoSuchKey/NotFound; a missing *bucket*
    (``NoSuchBucket``) re-raises the real ``botocore.exceptions.ClientError``
    — previously uncaught here, it fell through to a generic 500.
    """
    moto = pytest.importorskip("moto")
    with moto.mock_aws():
        # No bucket is ever created under the mock, so this raises
        # NoSuchBucket -- a real ClientError, not the caught 404/NoSuchKey.
        r = client.post("/exists", data={"key": "some/key", **_FAKE_CRED})
    assert r.status_code == 502
