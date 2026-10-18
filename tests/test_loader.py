"""Task 1.3 (loader): the graph in FalkorDB matches the generated world and ground truth."""
import pytest

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA, BETA
from causeway.graph.client import get_db


@pytest.fixture(scope="module")
def loaded():
    db = get_db()
    a, b = db.select_graph("loader_test_alpha"), db.select_graph("loader_test_beta")
    wa, wb = generate(ALPHA, 42), generate(BETA, 42)
    load_world(a, wa)
    load_world(b, wb)
    yield a, b, wa, wb
    a.delete()
    b.delete()


def count(g, q, **p):
    return g.ro_query(q, p).result_set[0][0]


def test_counts_match_world(loaded):
    a, _, wa, _ = loaded
    assert count(a, "MATCH (n) RETURN count(n)") == sum(len(v) for v in wa.nodes.values())
    assert count(a, "MATCH ()-[e]->() RETURN count(e)") == len(wa.edges)


def test_reload_is_clean_not_duplicated(loaded):
    a, _, wa, _ = loaded
    load_world(a, wa)
    assert count(a, "MATCH (n) RETURN count(n)") == sum(len(v) for v in wa.nodes.values())


def test_culprit_commit_modified_culprit_service(loaded):
    a, _, wa, _ = loaded
    for t in wa.truth["incidents"]:
        got = count(a, "MATCH (c:Commit {id: $c})-[:MODIFIED]->(s:Service {id: $s}) RETURN count(s)",
                    c=t["root_cause_commit"], s=t["root_cause_service"])
        assert got == 1


def test_why_path_exists_via_depends_on(loaded):
    a, _, wa, _ = loaded
    for t in wa.truth["incidents"]:
        if t["hops"] == 0:
            continue
        rows = a.ro_query(
            "MATCH p = (f:Service {id: $f})-[:DEPENDS_ON*1..4]->(c:Service {id: $c}) "
            "WHERE length(p) = $h RETURN count(p)",
            {"f": t["failing_service"], "c": t["root_cause_service"], "h": t["hops"]}).result_set
        assert rows[0][0] >= 1


def test_no_answers_loaded(loaded):
    a, _, _, _ = loaded
    assert count(a, "MATCH ()-[e:CAUSED_BY]->() RETURN count(e)") == 0
    assert count(a, "MATCH (i:Incident) WHERE i.family IS NOT NULL OR i.tier IS NOT NULL RETURN count(i)") == 0


def test_vector_index_finds_runbook(loaded):
    a, _, _, _ = loaded
    from causeway.embed import embed
    rows = a.ro_query(
        "CALL db.idx.vector.queryNodes('Doc', 'embedding', 1, vecf32($q)) YIELD node RETURN node.title",
        {"q": embed("ledger runbook")}).result_set
    assert rows[0][0] == "ledger runbook"


def test_tenants_have_disjoint_content(loaded):
    a, b, _, _ = loaded
    assert count(b, "MATCH (s:Service {name: 'payments'}) RETURN count(s)") == 0
    assert count(a, "MATCH (s:Service {name: 'routing'}) RETURN count(s)") == 0
