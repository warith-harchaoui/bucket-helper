"""
Unit tests for ``bucket_helper`` using ``moto`` to mock S3 in-process.

No real AWS / MinIO endpoint needed; runs by default. Real-endpoint
integration tests would go in a separate ``test_s3_helper_integration.py``
behind the ``integration`` marker.
"""

import json
import os

import pytest
import yaml

import bucket_helper as bh

# moto is in dev extras; if absent, skip the whole module gracefully.
moto = pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402


CRED_KEYS = {
    "s3_access_key": "AKIAFAKEFAKEFAKEFAKE",
    "s3_secret_key": "fakesecretfakesecretfakesecretfakesecret",
    "s3_bucket": "test-bucket",
    "s3_https": "https://test-bucket.s3.amazonaws.com",
    "s3_region": "us-east-1",
}


# ---------------------------------------------------------------------------
# credentials() — config loader
# ---------------------------------------------------------------------------


def test_credentials_from_json(tmp_path):
    cfg = tmp_path / "s3_config.json"
    cfg.write_text(json.dumps(CRED_KEYS))
    cred = bh.credentials(str(cfg))
    for k, v in CRED_KEYS.items():
        assert cred[k] == v


def test_credentials_from_yaml(tmp_path):
    cfg = tmp_path / "s3_config.yaml"
    cfg.write_text(yaml.safe_dump(CRED_KEYS))
    cred = bh.credentials(str(cfg))
    for k, v in CRED_KEYS.items():
        assert cred[k] == v


def test_credentials_from_env(monkeypatch, tmp_path):
    for k, v in CRED_KEYS.items():
        monkeypatch.setenv(k.upper(), v)
    cred = bh.credentials(str(tmp_path))
    for k, v in CRED_KEYS.items():
        assert cred[k] == v


def test_credentials_missing_key_raises(tmp_path):
    incomplete = {k: v for k, v in CRED_KEYS.items() if k != "s3_https"}
    cfg = tmp_path / "s3_config.json"
    cfg.write_text(json.dumps(incomplete))
    with pytest.raises(RuntimeError):
        bh.credentials(str(cfg))


# ---------------------------------------------------------------------------
# Mocked S3 fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def s3_cred(monkeypatch):
    """Activate moto and yield a credentials dict pointing at the mock."""
    # moto needs SOMETHING for the env credentials; use ours.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", CRED_KEYS["s3_access_key"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", CRED_KEYS["s3_secret_key"])
    monkeypatch.setenv("AWS_DEFAULT_REGION", CRED_KEYS["s3_region"])
    with mock_aws():
        bh.make_bucket(CRED_KEYS["s3_bucket"], CRED_KEYS)
        yield dict(CRED_KEYS)


# ---------------------------------------------------------------------------
# upload / exists / download / delete
# ---------------------------------------------------------------------------


def test_upload_download_roundtrip(s3_cred, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello s3")

    uri = bh.upload(str(src), s3_cred, "folder/src.txt")
    assert uri == "s3://test-bucket/folder/src.txt"
    assert bh.exists(uri, s3_cred) is True

    dst = tmp_path / "downloaded.txt"
    bh.download(uri, str(dst), s3_cred)
    assert dst.read_text() == "hello s3"


def test_upload_random_key_when_address_empty(s3_cred, tmp_path):
    src = tmp_path / "anon.bin"
    src.write_bytes(b"\x00\x01\x02")
    uri = bh.upload(str(src), s3_cred)
    assert uri.startswith("s3://test-bucket/")
    assert uri.endswith(".bin")
    assert bh.exists(uri, s3_cred) is True


def test_upload_random_key_honors_s3_prefix(s3_cred, tmp_path):
    src = tmp_path / "p.txt"
    src.write_text("x")
    cred = {**s3_cred, "s3_prefix": "snapshots"}
    uri = bh.upload(str(src), cred)
    assert uri.startswith("s3://test-bucket/snapshots/")


def test_exists_returns_false_for_missing(s3_cred):
    assert bh.exists("missing/nope.txt", s3_cred) is False


def test_delete_is_idempotent(s3_cred, tmp_path):
    # delete on missing must not raise.
    assert bh.delete("does-not-exist.txt", s3_cred) is True

    # Upload, then delete twice — second delete still succeeds.
    src = tmp_path / "v.txt"
    src.write_text("v")
    uri = bh.upload(str(src), s3_cred, "v.txt")
    assert bh.exists(uri, s3_cred)
    assert bh.delete(uri, s3_cred) is True
    assert bh.exists(uri, s3_cred) is False
    assert bh.delete(uri, s3_cred) is True  # second call still True


# ---------------------------------------------------------------------------
# list_prefix
# ---------------------------------------------------------------------------


def test_list_prefix(s3_cred, tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("x")
    for i in range(5):
        bh.upload(str(src), s3_cred, f"batch/{i:03}.txt")
    keys = bh.list_prefix("batch/", s3_cred)
    assert len(keys) == 5
    assert all(k.startswith("batch/") for k in keys)


def test_list_prefix_max_keys(s3_cred, tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("x")
    for i in range(7):
        bh.upload(str(src), s3_cred, f"capped/{i}.txt")
    keys = bh.list_prefix("capped/", s3_cred, max_keys=3)
    assert len(keys) == 3


# ---------------------------------------------------------------------------
# remote_tempfile
# ---------------------------------------------------------------------------


def test_remote_tempfile_cleans_on_exit(s3_cred, tmp_path):
    src = tmp_path / "tmp.json"
    src.write_text('{"a": 1}')

    with bh.remote_tempfile(s3_cred, ext="json", prefix="run-42") as (addr, url):
        assert addr.startswith("s3://test-bucket/run-42/")
        assert addr.endswith(".json")
        assert url.startswith("https://test-bucket.s3.amazonaws.com/run-42/")
        bh.upload(str(src), s3_cred, addr, content_type="application/json")
        assert bh.exists(addr, s3_cred) is True
        seen = addr

    assert bh.exists(seen, s3_cred) is False


def test_remote_tempfile_cleans_on_exception(s3_cred, tmp_path):
    src = tmp_path / "raises.txt"
    src.write_text("hi")

    seen = {}
    with pytest.raises(RuntimeError, match="boom"):
        with bh.remote_tempfile(s3_cred, ext="txt") as (addr, _url):
            bh.upload(str(src), s3_cred, addr)
            seen["addr"] = addr
            raise RuntimeError("boom")

    assert bh.exists(seen["addr"], s3_cred) is False


def test_remote_tempfile_uses_default_s3_prefix(s3_cred, tmp_path):
    cred = {**s3_cred, "s3_prefix": "uploads"}
    with bh.remote_tempfile(cred) as (addr, url):
        # No ext, no prefix arg → just bucket/uploads/<hex>
        assert addr.startswith("s3://test-bucket/uploads/")
        assert url.startswith("https://test-bucket.s3.amazonaws.com/uploads/")


# ---------------------------------------------------------------------------
# strip_s3_path / address parsing
# ---------------------------------------------------------------------------


def test_strip_s3_path_with_full_uri(s3_cred):
    assert bh.strip_s3_path("s3://my-bucket/path/to/obj", s3_cred) == "path/to/obj"


def test_strip_s3_path_with_key_only(s3_cred):
    assert bh.strip_s3_path("path/to/obj", s3_cred) == "path/to/obj"
