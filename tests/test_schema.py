"""Task 1.2: schema creation is idempotent and the vector index answers queries."""
import pytest

from causeway.graph.client import get_db
from causeway.graph.schema import (
    EMBEDDING_DIM, RANGE_INDEXES, VECTOR_INDEXES, ensure_schema, existing_indexes,
)


@pytest.fixture
def graph():
    g = get_db().select_graph("schema_test")
    yield g
    g.delete()


def test_ensure_schema_is_idempotent(graph):
    first = ensure_schema(graph)
    assert len(first) == len(RANGE_INDEXES) + len(VECTOR_INDEXES)
    assert ensure_schema(graph) == []  # second run creates nothing, no error


def test_expected_indexes_exist(graph):
    ensure_schema(graph)
    have = existing_indexes(graph)
    for label, prop in RANGE_INDEXES:
        assert (label, prop, "RANGE") in have
    for label, prop in VECTOR_INDEXES:
        assert (label, prop, "VECTOR") in have


def test_vector_index_returns_nearest(graph):
    ensure_schema(graph)
    near = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
    far = [0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2)
    for doc_id, vec in (("near", near), ("far", far)):
        graph.query("CREATE (:Doc {id: $id, embedding: vecf32($v)})", {"id": doc_id, "v": vec})
    rows = graph.ro_query(
        "CALL db.idx.vector.queryNodes('Doc', 'embedding', 1, vecf32($q)) "
        "YIELD node RETURN node.id",
        {"q": [0.9, 0.1] + [0.0] * (EMBEDDING_DIM - 2)},
    ).result_set
    assert rows == [["near"]]
