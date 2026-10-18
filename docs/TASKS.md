# Tasks (compressed scope; replaces the schedule in PLAN.md section 8)

Deadline: Oct 18, 2026, 11:29 AM PDT. Status: [x] done, [ ] todo.

## Scope
- 12 incidents in 4 recurring families (3 each), 10 services, a few hundred commits. Seeded, with `ground_truth.json`.
- MCP tools: find_entry_points, trace_dependencies, recent_changes, rank_suspects, similar_incidents, who_knows, decision_trace, recall, remember_episode.
- Two agents (triage, root-cause) coordinating through Task/Handoff nodes, plus a deterministic path verifier.
- Eval systems: flat RAG, graph agents without memory, graph agents with memory.
- Tests: path faithfulness, tenant isolation, concurrency, supersession.
- UI: one static page, chat stream plus Cytoscape why-path highlight.
- Local `make demo`; hosted deploy only if time is left.
- Cut: comms agent, memory timeline, counterfactual, LLM-only baseline. Action tools (file_ticket) undecided.

## Day 1: Foundation
- [x] 1.1 FalkorDB in Docker, Python client smoke test
- [x] 1.2 Schema and indexes (range + vector), idempotent `make schema`
- [x] 1.3 Seeded generator, `make seed` for tenant_alpha and tenant_beta, ground_truth.json
- [x] 1.4 Cypher query library (`.cypher` files), each tested against ground truth
- [x] 1.5 Eval harness skeleton + flat RAG baseline

## Day 2: Tools, Track 3, Track 1
- [x] 2.1 MCP server with read tools and ToolCall audit trail
- [x] 2.2 Path verifier + test_path_faithfulness
- [x] 2.3 Graph agents (no memory) scored on all incidents (deterministic agents, no LLM)
- [ ] 2.4 Company-brain Q&A with cited paths (not done: who_knows/decision_trace exist as tools, no Q&A mode)

## Day 3: Memory and coordination
- [x] 3.1 remember_episode + recall
- [x] 3.2 Belief supersession + test_supersession
- [x] 3.3 Triage / root-cause split with Task/Handoff + atomic claim, test_concurrency
- [x] 3.4 Memory-enabled run in chronological order, learning curve
- [x] 3.5 Tenant binding at MCP session level + test_tenant_isolation

## Day 4: UI and polish
- [x] 4.1 Static page: chat stream + Cytoscape why-path
- [ ] 4.2 Fix worst eval misses (not done: weights deliberately not tuned)
- [x] 4.3 Full eval, auto-generated docs/RESULTS.md
- [x] 4.4 README: graph model, Cypher list, results table

## Day 5: Ship
- [x] 5.1 `make demo` verified from a clean clone
- [ ] 5.2 Demo video (3 min max)
- [ ] 5.3 Public repo, final AI_DISCLOSURE.md
- [ ] 5.4 Submit with all three tracks
