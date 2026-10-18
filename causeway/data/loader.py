"""Load a generated world into a tenant graph:  python -m causeway.data.loader [seed]

Labels and relationship types cannot be Cypher parameters, so they are checked
against the schema's label list / an UPPER_SNAKE pattern before going into the
query text. All data values go through parameters.
"""
import re
import sys
from collections import defaultdict

from falkordb import Graph

from causeway.data.generate import World, generate, write
from causeway.data.specs import ALPHA, BETA
from causeway.embed import embed
from causeway.graph.client import get_db
from causeway.graph.schema import LABELS, ensure_schema

BATCH = 500
REL = re.compile(r"^[A-Z_]+$")


def _chunks(rows):
    for i in range(0, len(rows), BATCH):
        yield rows[i:i + BATCH]


def load_world(graph: Graph, world: World) -> dict:
    """Wipe `graph`, create indexes, load nodes then edges. Returns counts."""
    try:
        graph.delete()
    except Exception:  # graph did not exist yet
        pass
    ensure_schema(graph)

    for label, rows in world.nodes.items():
        assert label in LABELS, label
        if label == "Doc":
            rows = [dict(r, embedding=embed(f"{r['title']} {r['body']}")) for r in rows]
            q = f"UNWIND $rows AS r CREATE (n:{label}) SET n = r, n.embedding = vecf32(r.embedding)"
        else:
            q = f"UNWIND $rows AS r CREATE (n:{label}) SET n = r"
        for chunk in _chunks(rows):
            graph.query(q, {"rows": chunk})

    groups = defaultdict(list)
    for e in world.edges:
        groups[(e["src"][0], e["rel"], e["dst"][0])].append(dict(s=e["src"][1], d=e["dst"][1], p=e["props"]))
    for (sl, rel, dl), rows in groups.items():
        assert sl in LABELS and dl in LABELS and REL.match(rel), (sl, rel, dl)
        q = (f"UNWIND $rows AS r MATCH (a:{sl} {{id: r.s}}), (b:{dl} {{id: r.d}}) "
             f"CREATE (a)-[e:{rel}]->(b) SET e = r.p")
        for chunk in _chunks(rows):
            graph.query(q, {"rows": chunk})
    return dict(nodes=sum(len(v) for v in world.nodes.values()), edges=len(world.edges))


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    db = get_db()
    for spec in (ALPHA, BETA):
        world = generate(spec, seed)
        write(world, __import__("pathlib").Path("data"))
        counts = load_world(db.select_graph(f"tenant_{spec.tenant}"), world)
        print(f"tenant_{spec.tenant}: loaded {counts['nodes']} nodes, {counts['edges']} edges")
