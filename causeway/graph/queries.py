"""Run the .cypher files in causeway/graph/queries/ by name.

    rows = run(graph, "who_knows", service="svc-payments")   # -> list[dict]

Every product query is a file there (header comment says what it is for);
parameters are always passed through FalkorDB params, never formatted in.
Reads use ro_query so a query file cannot write by accident.
"""
from functools import cache
from pathlib import Path

from falkordb import Graph

QUERY_DIR = Path(__file__).parent / "queries"


@cache
def load(name: str) -> str:
    return (QUERY_DIR / f"{name}.cypher").read_text()


def run(graph: Graph, name: str, **params) -> list[dict]:
    res = graph.ro_query(load(name), params)
    cols = [h[1] for h in res.header]
    return [dict(zip(cols, row)) for row in res.result_set]


def write(graph: Graph, name: str, **params) -> list[dict]:
    """Same as run() but allowed to modify the graph (memory writes)."""
    res = graph.query(load(name), params)
    cols = [h[1] for h in res.header]
    return [dict(zip(cols, row)) for row in res.result_set]
