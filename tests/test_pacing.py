"""Pacing: one client per credential set, jittered gaps between requests."""

from types import SimpleNamespace

from bucket_helper import main as bh_main

CRED = {"s3_access_key": "a", "s3_secret_key": "s", "s3_bucket": "b", "s3_https": "https://x"}


def _clock(monkeypatch):
    now = [1000.0]
    sleeps = []
    monkeypatch.setattr(bh_main.time, "monotonic", lambda: now[0])

    def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(bh_main.time, "sleep", fake_sleep)
    return sleeps


def test_requests_to_one_host_are_spaced_randomly(monkeypatch):
    sleeps = _clock(monkeypatch)
    monkeypatch.setattr(bh_main, "_PACE", (0.3, 1.5))
    for _ in range(6):
        bh_main._pace_hook(SimpleNamespace(url="https://s3.fr-par.scw.cloud/b/k"))
    assert len(sleeps) == 5 and all(0.3 <= s <= 1.5 for s in sleeps)
    assert len(set(sleeps)) > 1


def test_hosts_are_paced_independently(monkeypatch):
    sleeps = _clock(monkeypatch)
    monkeypatch.setattr(bh_main, "_PACE", (1.0, 2.0))
    bh_main._pace_hook(SimpleNamespace(url="https://one.example/b/k"))
    bh_main._pace_hook(SimpleNamespace(url="https://two.example/b/k"))
    assert sleeps == []


def test_zero_range_disables_pacing(monkeypatch):
    sleeps = _clock(monkeypatch)
    for _ in range(3):
        bh_main._pace_hook(SimpleNamespace(url="https://one.example/b/k"))
    assert sleeps == []


def test_one_client_per_credential_set_reused(monkeypatch):
    built = []
    monkeypatch.setattr(bh_main, "_build_client", lambda cred: built.append(1) or object())
    with bh_main.get_client_s3(CRED) as c1, bh_main.get_client_s3(dict(CRED)) as c2:
        assert c1 is c2
    with bh_main.get_client_s3({**CRED, "s3_secret_key": "other"}) as c3:
        assert c3 is not c1
    assert len(built) == 2


def test_every_request_of_a_real_client_is_paced(monkeypatch):
    # Behavior, not wiring: two calls through moto's in-process S3 must sleep
    # between their HTTP requests.
    import boto3
    from moto import mock_aws

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="pace-bucket")
        sleeps = _clock(monkeypatch)
        monkeypatch.setattr(bh_main, "_PACE", (0.3, 1.5))
        cred = {**CRED, "s3_region": "us-east-1"}
        bh_main.exists("s3://pace-bucket/missing-1", cred)
        bh_main.exists("s3://pace-bucket/missing-2", cred)
        assert sleeps and all(0.3 <= s <= 1.5 for s in sleeps)


def test_retry_mode_is_configurable():
    client = bh_main._build_client({**CRED, "s3_retry_mode": "adaptive"})
    assert client.meta.config.retries["mode"] == "adaptive"


def test_unknown_retry_mode_falls_back_to_standard():
    client = bh_main._build_client({**CRED, "s3_retry_mode": "turbo"})
    assert client.meta.config.retries["mode"] == "standard"


def test_env_range_parsing(monkeypatch):
    monkeypatch.setenv("X_PACE", "4,1")
    assert bh_main._env_range("X_PACE", (0, 0)) == (1.0, 4.0)
    monkeypatch.setenv("X_PACE", "bad")
    assert bh_main._env_range("X_PACE", (2.0, 3.0)) == (2.0, 3.0)
