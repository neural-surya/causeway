from causeway.data.generate import dependency_path
from causeway.data.specs import ALPHA
from causeway.graph.queries import run


def test_dependents_match_independent_bfs(graph):
    names = list(ALPHA.services)
    expect = {f"svc-{b}": sum(1 for a in names if a != b and dependency_path(ALPHA.deps, a, b))
              for b in names}
    got = {r["service"]: r["dependents"] for r in run(graph, "service_features")}
    assert got == expect


def test_flaky_and_test_counts_match_world(graph, world):
    covers = {e["src"][1]: e["dst"][1] for e in world.edges if e["rel"] == "COVERS"}
    flaky = {t["id"]: t["flaky_score"] for t in world.nodes["Test"]}
    rows = {r["service"]: r for r in run(graph, "service_features")}
    for svc, r in rows.items():
        mine = [flaky[t] for t, s in covers.items() if s == svc]
        assert r["tests"] == len(mine)
        assert abs(r["max_flaky"] - max(mine)) < 1e-9


def test_leaf_dependency_has_most_dependents(graph):
    rows = {r["service"]: r["dependents"] for r in run(graph, "service_features")}
    assert rows["svc-user-profile"] > rows["svc-api-gateway"] == 0
