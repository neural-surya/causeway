from causeway.ranking import rank_suspects


def test_ranking_is_sorted_and_bounded_by_incident_time(graph, truth):
    for iid, t in truth.items():
        rows = rank_suspects(graph, iid)
        assert rows == sorted(rows, key=lambda r: -r["score"])
        assert all(r["ts"] <= t["ts"] for r in rows)


def test_easy_tier_culprit_ranks_first(graph, truth):
    for t in truth.values():
        if t["tier"] == "easy":
            assert rank_suspects(graph, t["incident"])[0]["commit"] == t["root_cause_commit"]


def test_decoys_beat_culprit_on_hard_tier_without_memory(graph, truth):
    # the generator plants decoys that are newer and closer, so a structure-only ranker must struggle
    misses = [t for t in truth.values() if t["tier"] == "hard"
              and rank_suspects(graph, t["incident"])[0]["commit"] != t["root_cause_commit"]]
    assert misses
