from causeway.graph.queries import run


def nearest(rows, key):
    best = {}
    for r in rows:
        best[r[key]] = min(best.get(r[key], 99), r["hops"])
    return best


def test_culprit_reachable_at_ground_truth_hops(graph, truth):
    for t in truth.values():
        if t["hops"] == 0:
            continue
        rows = run(graph, "trace_dependencies", service=t["failing_service"], depth=4)
        assert nearest(rows, "dependency")[t["root_cause_service"]] == t["hops"]


def test_a_returned_path_equals_the_expected_why_path(graph, truth):
    for t in truth.values():
        if t["hops"] == 0:
            continue
        rows = run(graph, "trace_dependencies", service=t["failing_service"], depth=4)
        paths = [r["path_ids"] for r in rows if r["dependency"] == t["root_cause_service"]]
        assert t["why_path"] in paths


def test_depth_limit_is_respected(graph):
    rows = run(graph, "trace_dependencies", service="svc-api-gateway", depth=1)
    assert rows and all(r["hops"] == 1 for r in rows)


def test_leaf_service_has_no_dependencies(graph):
    assert run(graph, "trace_dependencies", service="svc-user-profile", depth=4) == []


def test_dependents_are_the_reverse(graph):
    up = nearest(run(graph, "dependents", service="svc-ledger", depth=4), "dependent")
    assert up["svc-payments"] == 1 and up["svc-billing"] == 1 and up["svc-api-gateway"] == 2
    assert "svc-user-profile" not in up
