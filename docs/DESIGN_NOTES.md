# Design notes

## 1.1 FalkorDB + client
- One FalkorDB instance, one graph per tenant (`tenant_<id>`), so isolation is structural.
- Reads use `ro_query`, writes `query`; all values go through `params`, never string formatting.

## 1.2 Schema and indexes
- Range index on `id` for every label (fast lookup by id), plus `Incident.ts` and `Commit.ts` for time-window queries.
- Vector index on `Doc.embedding` and `Belief.embedding`: 384 dims (all-MiniLM-L6-v2), cosine. Vector search only finds entry points; graph traversal does the reasoning.
- Verified on the live DB: a duplicate `CREATE INDEX` raises an error, so `ensure_schema` reads `CALL db.indexes()` first and creates only what is missing.
- `ro_query` on a graph that does not exist yet fails with "empty key"; we treat that as "no indexes yet".
- Vector `score` from `db.idx.vector.queryNodes` is a cosine distance (lower = closer).
- Index DDL uses f-strings because labels cannot be parameters in Cypher; they come from the constant lists in `schema.py`, never from user input.

## 1.3 Synthetic world, ground truth, loader
- `specs.py` is config only (services, DAG, teams, families, decisions); `generate.py` is the logic. Everything derives from `random.Random(f"{seed}:{tenant}")` and a fixed END date (2026-10-15), never `now()`, so the same seed gives byte-identical output.
- alpha "Northwind Payments": 10 services, 4 teams, 16 people, 645 nodes (~300 commits), 12 incidents = 4 families x 3 occurrences. beta "Globex Logistics": 4 services, 2 incidents, different names so any cross-tenant leak is detectable.
- Families (tier fixed per family): retry = easy (culprit in the failing service, 0 hops); schema = medium and flaky = medium (culprit 2 hops up); config = hard (2 hops, misleading culprit message, 2 innocent decoy commits that are *more recent* than the culprit, so recency alone ranks wrong). Medium has 1 decoy.
- Incidents are interleaved by family (retry, schema, config, flaky, retry, ...) so memory from occurrence 1 can help occurrence 2 and 3.
- **Answers are not in the graph.** `ground_truth.json` holds family, tier, culprit commit/service, hops and the expected why-path. The graph has no `CAUSED_BY` edges and Incident nodes carry no family/tier. Otherwise the agents could just read the answer. Later, resolved incidents get their `CAUSED_BY` through `remember_episode`.
- Incident nodes carry one extra property, `summary` (the alert text), used by `find_entry_points`. Not in PLAN.md's property list.
- `KNOWS_ABOUT.weight` = number of commits the person authored on the service (kept when >= 3). Fact edges carry `valid_from`; none has `valid_to` yet.
- Loader: wipes the tenant graph, runs `ensure_schema`, loads nodes then edges with `UNWIND $rows`. Labels/relationship types are validated before going into the query text (they cannot be parameters). Docs get embeddings from the hashed stand-in.
- FalkorDB finding: on this build, a variable-length pattern with min == max (`*2`, `*2..2`) returns 0 rows. Use `*1..N` plus `WHERE length(p) = $h`. Variable-length matches return every path, not only the shortest (api-gateway to fraud gives lengths 2 and 3).
- The server query TIMEOUT defaults to 1000 ms; keep it in mind for the concurrency test.
