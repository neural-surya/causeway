import pytest
from fastapi.testclient import TestClient

from causeway import api
from causeway.session import Session


@pytest.fixture
def client(graph, monkeypatch):
    monkeypatch.setattr(api, "session", Session("alpha", graph))
    return TestClient(api.app)


def test_page_and_health(client):
    assert client.get("/").status_code == 200 and "Causeway" in client.get("/").text
    assert client.get("/static/cytoscape.min.js").status_code == 200
    assert client.get("/api/health").json() == {"ok": True}


def test_incident_list_and_investigate(client):
    rows = client.get("/api/incidents").json()
    assert len(rows) == 12 and rows[0]["id"] == "inc-01"
    r = client.post("/api/investigate", json={"incident": "inc-01", "memory": False}).json()
    assert r["claims"][0]["verified"] and r["elements"]["nodes"]


def test_unknown_incident_is_404(client):
    assert client.post("/api/investigate", json={"incident": "inc-99"}).status_code == 404
    assert client.post("/api/resolve", json={"incident": "inc-99"}).status_code == 404


def test_resolve_marks_incident_remembered(client):
    assert client.post("/api/resolve", json={"incident": "inc-02"}).json()["remembered"] == "inc-02"
    row = next(r for r in client.get("/api/incidents").json() if r["id"] == "inc-02")
    assert row["remembered"] is True
