from causeway.investigate import investigate, resolve
from causeway.session import Session


def test_investigation_produces_verified_claims_and_agent_handoff(graph, truth):
    s = Session("alpha", graph)
    r = investigate(s, "inc-01", use_memory=False)
    assert r["claims"] and all(c["verified"] for c in r["claims"])
    assert r["suspects"][0]["commit"] == truth["inc-01"]["root_cause_commit"]
    agents = [st["agent"] for st in r["steps"]]
    assert agents.index("root-cause") > max(i for i, a in enumerate(agents) if a == "triage")
    status = graph.ro_query("MATCH (t:Task {id: $t}) RETURN t.status", {"t": r["task"]}).result_set
    assert status == [["claimed"]]
    assert {e["data"]["id"] for e in r["elements"]["nodes"]} >= {"svc-payments", truth["inc-01"]["root_cause_commit"]}


def test_memory_changes_the_ranking_of_a_repeat_family(world):
    from causeway.data.loader import load_world
    from causeway.graph.client import get_db
    g = get_db().select_graph("investigate_mem_test")
    try:
        load_world(g, world)
        s = Session("alpha", g)
        t1 = next(t for t in world.truth["incidents"] if t["incident"] == "inc-02")  # schema, 1st occurrence
        t2 = next(t for t in world.truth["incidents"] if t["incident"] == "inc-06")  # schema, 2nd occurrence
        msg = next(c["msg"] for c in world.nodes["Commit"] if c["id"] == t1["root_cause_commit"])
        before = investigate(s, "inc-06", use_memory=True)
        resolve(s, "inc-02", t1["root_cause_commit"], msg, t1["ts"] + 3600)
        after = investigate(s, "inc-06", use_memory=True)
        assert after["suspects"][0]["commit"] == t2["root_cause_commit"]
        assert any(x["memory_boost"] > 1 for x in after["suspects"])
        assert all(x["memory_boost"] == 1 for x in before["suspects"])
    finally:
        g.delete()
