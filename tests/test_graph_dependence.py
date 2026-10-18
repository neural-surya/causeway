"""FalkorDB is the only store: with it unreachable the product does not work (no silent fallback)."""
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from causeway.session import Session


def test_session_cannot_work_without_falkordb(monkeypatch):
    monkeypatch.setenv("FALKORDB_PORT", "6399")  # nothing listens here
    with pytest.raises((RedisConnectionError, ConnectionError)):
        Session("alpha").who_knows("svc-payments")


def test_health_endpoint_fails_without_falkordb(monkeypatch):
    from fastapi.testclient import TestClient
    from causeway import api
    monkeypatch.setenv("FALKORDB_PORT", "6399")
    broken = Session.__new__(Session)
    from causeway.graph.client import get_db
    broken.graph = get_db().select_graph("tenant_alpha")
    monkeypatch.setattr(api, "session", broken)
    with pytest.raises((RedisConnectionError, ConnectionError)):
        TestClient(api.app).get("/api/health")
