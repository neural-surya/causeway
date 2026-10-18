import pytest

from causeway.graph.queries import run


def test_incident_context_matches_world(graph, world, truth):
    for iid, t in truth.items():
        [row] = run(graph, "incident_context", incident=iid)
        assert row["service_id"] == t["failing_service"]
        assert row["ts"] == t["ts"]


def test_unknown_incident_returns_nothing(graph):
    assert run(graph, "incident_context", incident="inc-99") == []


def test_missing_query_file_is_an_error(graph):
    with pytest.raises(FileNotFoundError):
        run(graph, "nope")
