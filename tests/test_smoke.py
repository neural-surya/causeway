"""Task 1.1: FalkorDB is reachable and we can create/read a node in a named graph."""
from causeway.graph.client import get_db

SMOKE = "smoke_test"


def test_create_and_read_node():
    graph = get_db().select_graph(SMOKE)
    try:
        graph.query("CREATE (:Service {id: $id, name: $name})", {"id": "svc-1", "name": "payments"})
        rows = graph.ro_query("MATCH (s:Service {id: $id}) RETURN s.name", {"id": "svc-1"}).result_set
        assert rows == [["payments"]]
    finally:
        graph.delete()
