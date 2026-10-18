import pytest

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA
from causeway.graph.client import get_db
from causeway.memory import recall, remember_episode, supersede_belief


@pytest.fixture
def mem():
    g = get_db().select_graph("memory_test_alpha")
    w = generate(ALPHA, 42)
    load_world(g, w)
    yield g, {t["incident"]: t for t in w.truth["incidents"]}
    g.delete()


def test_remember_then_recall_surfaces_the_episode(mem):
    g, truth = mem
    t = truth["inc-01"]
    remember_episode(g, "inc-01", t["root_cause_commit"], "retry without backoff", t["ts"] + 7200)
    assert recall(g, as_of=t["ts"]) == []                       # not yet resolved at incident time
    [b] = recall(g, as_of=truth["inc-05"]["ts"])
    assert b["commit"] == t["root_cause_commit"] and b["incident"] == "inc-01"


def test_remember_is_idempotent(mem):
    g, truth = mem
    t = truth["inc-01"]
    for _ in range(3):
        remember_episode(g, "inc-01", t["root_cause_commit"], "retry", t["ts"] + 7200)
    assert len(recall(g, as_of=t["ts"] + 10**6)) == 1
    n = g.ro_query("MATCH (e:Episode) RETURN count(e)").result_set[0][0]
    assert n == 1


def test_resolved_incident_gets_caused_by_only_after_memory_write(mem):
    g, truth = mem
    q = "MATCH (:Incident)-[e:CAUSED_BY]->(:Commit) RETURN count(e)"
    assert g.ro_query(q).result_set[0][0] == 0
    remember_episode(g, "inc-01", truth["inc-01"]["root_cause_commit"], "x", truth["inc-01"]["ts"] + 1)
    assert g.ro_query(q).result_set[0][0] == 1
