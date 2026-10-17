"""Indexes for a tenant graph. Idempotent: existing indexes are skipped.

FalkorDB raises "Attribute 'x' is already indexed" on a duplicate CREATE INDEX,
so we read CALL db.indexes() first and only create what is missing.
"""
import sys

from falkordb import Graph
from redis.exceptions import ResponseError

from causeway.graph.client import tenant_graph

EMBEDDING_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2

LABELS = [
    # company brain
    "Person", "Team", "Service", "Commit", "PR", "Test", "Ticket",
    "Incident", "Decision", "Doc", "Thread",
    # memory + coordination
    "Episode", "Belief", "Playbook", "PlaybookStep", "ToolCall",
    "Agent", "Task", "Handoff",
]
RANGE_INDEXES = [(label, "id") for label in LABELS] + [("Incident", "ts"), ("Commit", "ts")]
VECTOR_INDEXES = [("Doc", "embedding"), ("Belief", "embedding")]


def existing_indexes(graph: Graph) -> set[tuple[str, str, str]]:
    """Set of (label, property, type) for node indexes, e.g. ('Doc', 'embedding', 'VECTOR')."""
    found = set()
    try:
        rows = graph.ro_query("CALL db.indexes()").result_set
    except ResponseError as e:
        if "empty key" in str(e):  # graph does not exist yet: first CREATE INDEX will make it
            return found
        raise
    for label, props, types, *_ in rows:
        for prop in props:
            for kind in types[prop]:
                found.add((label, prop, kind))
    return found


def ensure_schema(graph: Graph) -> list[str]:
    """Create any missing indexes. Returns descriptions of what was created."""
    have = existing_indexes(graph)
    created = []
    for label, prop in RANGE_INDEXES:
        if (label, prop, "RANGE") not in have:
            graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
            created.append(f"RANGE {label}.{prop}")
    for label, prop in VECTOR_INDEXES:
        if (label, prop, "VECTOR") not in have:
            graph.query(
                f"CREATE VECTOR INDEX FOR (n:{label}) ON (n.{prop}) "
                f"OPTIONS {{dimension:{EMBEDDING_DIM}, similarityFunction:'cosine'}}"
            )
            created.append(f"VECTOR {label}.{prop}")
    return created


if __name__ == "__main__":
    tenants = sys.argv[1:] or ["alpha", "beta"]
    for t in tenants:
        made = ensure_schema(tenant_graph(t))
        print(f"tenant_{t}: created {len(made)} index(es)")
