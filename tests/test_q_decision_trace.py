from causeway.graph.queries import run


def test_retry_chain_for_payments(graph, world):
    rows = {r["decision"]: r for r in run(graph, "decision_trace", service="svc-payments")}
    title = {d["id"]: d["title"] for d in world.nodes["Decision"]}
    retry = [d for d, t in title.items() if "etry" in t]
    assert len(retry) == 3 and set(retry) <= set(rows)
    d1, d2, d3 = sorted(retry, key=lambda d: rows[d]["ts"])
    assert rows[d1]["superseded_by"] == d2 and rows[d2]["superseded_by"] == d3
    assert rows[d3]["superseded_by"] is None and rows[d3]["status"] == "active"


def test_superseded_decisions_are_exactly_those_with_a_successor(graph, world):
    for svc in ("svc-payments", "svc-user-profile", "svc-orders"):
        for r in run(graph, "decision_trace", service=svc):
            assert (r["superseded_by"] is not None) == (r["status"] == "superseded")


def test_every_decision_cites_a_document(graph):
    rows = run(graph, "decision_trace", service="svc-ledger")
    assert rows and all(r["doc"] and r["path_ids"][-1] == "svc-ledger" for r in rows)
