import pytest

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA
from causeway.graph.client import get_db
from causeway.memory import recall, remember_episode, supersede_belief


@pytest.fixture
def mem():
    g = get_db().select_graph("supersession_test_alpha")
    w = generate(ALPHA, 42)
    load_world(g, w)
    t = {x["incident"]: x for x in w.truth["incidents"]}["inc-01"]
    remember_episode(g, "inc-01", t["root_cause_commit"], "retry without backoff", t["ts"] + 100)
    yield g, t
    g.delete()


def test_supersession_keeps_history_and_recall_returns_current(mem):
    g, t = mem
    late = t["ts"] + 10**6
    supersede_belief(g, "bel-inc-01", "bel-inc-01-v2", "Actually the retry budget was the real cause",
                     "found the budget misconfiguration", t["ts"] + 5000)
    current = recall(g, as_of=late)
    assert [b["belief"] for b in current] == ["bel-inc-01-v2"]
    assert current[0]["commit"] == t["root_cause_commit"]       # links were carried over
    history = {b["belief"]: b for b in recall(g, as_of=late, include_history=True)}
    assert set(history) == {"bel-inc-01", "bel-inc-01-v2"}
    assert history["bel-inc-01"]["valid_to"] == t["ts"] + 5000  # old belief closed, not deleted


def test_supersedes_edge_records_the_reason(mem):
    g, t = mem
    supersede_belief(g, "bel-inc-01", "bel-inc-01-v2", "new", "because evidence changed", t["ts"] + 5000)
    rows = g.ro_query("MATCH (n:Belief)-[r:SUPERSEDES]->(o:Belief) RETURN n.id, o.id, r.reason").result_set
    assert rows == [["bel-inc-01-v2", "bel-inc-01", "because evidence changed"]]


def test_cannot_supersede_an_already_closed_belief(mem):
    g, t = mem
    supersede_belief(g, "bel-inc-01", "v2", "a", "r", t["ts"] + 5000)
    supersede_belief(g, "bel-inc-01", "v3", "b", "r", t["ts"] + 6000)  # old is closed: no-op
    n = g.ro_query("MATCH (b:Belief {id: 'v3'}) RETURN count(b)").result_set[0][0]
    assert n == 0
