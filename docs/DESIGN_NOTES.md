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
