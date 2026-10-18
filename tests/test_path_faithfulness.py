"""Fabricated claim paths must be rejected; real ones accepted."""
from causeway.graph.queries import run
from causeway.graph.verifier import verify_answer, verify_claim


def real_claim(graph, t):
    rows = run(graph, "recent_changes", service=t["failing_service"], depth=3, as_of=t["ts"], window_hours=72)
    row = next(r for r in rows if r["commit"] == t["root_cause_commit"])
    return dict(text="root cause", path_ids=row["path_ids"][:-1],
                entities=[t["failing_service"], t["root_cause_commit"]])


def test_real_root_cause_paths_verify_for_every_incident(graph, truth):
    for t in truth.values():
        assert verify_claim(graph, real_claim(graph, t)).ok, t["incident"]


def test_fabricated_edge_is_rejected(graph, truth):
    t = truth["inc-07"]
    bad = real_claim(graph, t)
    bad["path_ids"] = [t["failing_service"], t["root_cause_commit"]]  # skips the dependency chain
    v = verify_claim(graph, bad)
    assert not v.ok and "no relationship" in v.reason


def test_nonexistent_node_is_rejected(graph):
    v = verify_claim(graph, dict(path_ids=["svc-payments", "com-999"], entities=[]))
    assert not v.ok


def test_wrong_commit_for_service_is_rejected(graph, truth):
    t = truth["inc-01"]
    other = truth["inc-02"]["root_cause_commit"]  # modified svc-payments? check via claim below
    bad = dict(path_ids=["svc-ledger", other], entities=["svc-ledger", other])
    assert not verify_claim(graph, bad).ok


def test_entity_missing_from_path_is_rejected(graph, truth):
    t = truth["inc-07"]
    c = real_claim(graph, t)
    c["entities"].append("person-01")
    v = verify_claim(graph, c)
    assert not v.ok and "person-01" in v.reason


def test_short_path_is_rejected(graph):
    assert not verify_claim(graph, dict(path_ids=["svc-payments"], entities=[])).ok


def test_faithfulness_score(graph, truth):
    good = real_claim(graph, truth["inc-03"])
    bad = dict(path_ids=["svc-ledger", "com-001"], entities=[])
    r = verify_answer(graph, [good, bad])
    assert r["faithfulness"] == 0.5
