from causeway.data.specs import ALPHA
from causeway.graph.queries import run


def hood(svc):
    out, frontier = {svc}, {svc}
    for _ in range(2):
        frontier = {b for a, b in ALPHA.deps if a in frontier}
        out |= frontier
    return out


def test_scores_match_independent_jaccard(graph, truth):
    for iid, t in truth.items():
        mine = hood(t["failing_service"].removeprefix("svc-"))
        for r in run(graph, "similar_incidents", incident=iid):
            other = hood(truth[r["similar"]]["failing_service"].removeprefix("svc-"))
            assert abs(r["jaccard"] - len(mine & other) / len(mine | other)) < 1e-9


def test_only_earlier_incidents_are_returned(graph, truth):
    for iid, t in truth.items():
        assert all(truth[r["similar"]]["ts"] < t["ts"] for r in run(graph, "similar_incidents", incident=iid))
    assert run(graph, "similar_incidents", incident="inc-01") == []


def test_same_service_scores_one(graph, truth):
    rows = run(graph, "similar_incidents", incident="inc-10")  # payments, earlier payments incident inc-01
    assert next(r for r in rows if r["similar"] == "inc-01")["jaccard"] == 1.0
