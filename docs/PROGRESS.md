# Progress
One line per commit.

- repo scaffold + task 1.1: FalkorDB in docker compose, Python client smoke test
- README: hackathon link and tracks
- docs/TASKS.md: compressed task list with status
- schema: idempotent range + vector indexes per tenant graph, make schema
- embed: deterministic hashed bag-of-words stand-in (384 dims)
- data: seeded world generator (specs, generate.py, ground truth) with tests
- seed: loader + make seed for tenant_alpha/tenant_beta, graph tests vs ground truth
- queries: runner (queries.py), shared test fixtures, incident_context
- queries: trace_dependencies, dependents
- queries: recent_changes (as_of bounded, deduped, evidence path)
- queries: service_features (blast radius, flakiness)
- queries: who_knows (owners + experts)
- queries: decision_trace (supersession chain)
- queries: similar_incidents (neighbourhood Jaccard, earlier only)
- queries: entry_points (vector), service_for_test
- verifier: deterministic path verifier + test_path_faithfulness
