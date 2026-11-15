"""Shared test setup: no real pauses, and no client reused across tests.

``get_client_s3`` caches one client per credential set and paces every
request (see bucket_helper.main). Tests must not pay seconds per request, and
a client built under one test's moto mock must never serve the next test.
"""

import pytest

from bucket_helper import main as bh_main


@pytest.fixture(autouse=True)
def _fresh_clients_no_pacing(monkeypatch):
    monkeypatch.setattr(bh_main, "_PACE", (0.0, 0.0))
    bh_main._close_clients()
    bh_main._last_request.clear()
    yield
    bh_main._close_clients()
