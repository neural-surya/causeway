"""FalkorDB is the only store: with it unreachable the product does not work (no silent fallback)."""
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from causeway.session import Session


def test_session_cannot_work_without_falkordb(monkeypatch):
    monkeypatch.setenv("FALKORDB_PORT", "6399")  # nothing listens here
    with pytest.raises((RedisConnectionError, ConnectionError)):
        Session("alpha").who_knows("svc-payments")
