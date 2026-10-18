from causeway.graph.queries import run


def changes(graph, t, window=72, depth=3):
    return run(graph, "recent_changes", service=t["failing_service"], depth=depth,
               as_of=t["ts"], window_hours=window)


def test_culprit_is_in_candidates_for_every_incident(graph, truth):
    for t in truth.values():
        ids = {r["commit"] for r in changes(graph, t)}
        assert t["root_cause_commit"] in ids, t["incident"]


def test_culprit_hops_match_ground_truth(graph, truth):
    for t in truth.values():
        row = next(r for r in changes(graph, t) if r["commit"] == t["root_cause_commit"])
        assert row["hops"] == t["hops"] and row["service"] == t["root_cause_service"]


def test_never_returns_changes_after_the_incident(graph, truth):
    for t in truth.values():
        assert all(r["ts"] <= t["ts"] for r in changes(graph, t, window=24 * 30))


def test_each_commit_reported_once(graph, truth):
    for t in truth.values():
        ids = [r["commit"] for r in changes(graph, t, window=24 * 30)]
        assert len(ids) == len(set(ids))


def test_evidence_path_is_a_real_chain(graph, truth):
    t = truth["inc-07"]
    row = next(r for r in changes(graph, t) if r["commit"] == t["root_cause_commit"])
    # service chain, then the commit, then its author
    assert row["path_ids"] == t["why_path"] + [t["root_cause_commit"], row["author"]]


def test_narrow_window_excludes_old_changes(graph, truth):
    t = truth["inc-01"]
    assert len(changes(graph, t, window=1)) < len(changes(graph, t, window=24 * 30))
