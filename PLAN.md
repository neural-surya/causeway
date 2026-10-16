# CAUSEWAY — Build Plan for Claude Code
Graph Hacks (FalkorDB) · all three tracks · solo entry

> Hand this whole file to Claude Code. Copy section 0 into `CLAUDE.md` at the repo root so it persists across sessions.

---

## 0. Operating rules (copy into CLAUDE.md)

**Product in one line:** Causeway is a team of agents that investigates failing releases/incidents in a synthetic company and explains every conclusion with a verifiable path through a FalkorDB graph.

**Hard rules from the hackathon (never violate):**
1. FalkorDB is the primary datastore. If FalkorDB is removed, the product must stop working. No decorative graph. Never add a second primary store (SQLite/Postgres/Mongo for core state is forbidden; flat files for fixtures and eval results are fine).
2. Data is synthetic or public only. No real company, personal, or private data anywhere.
3. Main coding starts **Oct 14, 2026, 11:31 AM PDT** or later. Before that, only: schema sketches, Cypher drafts in `docs/`, diagrams, notes, repo scaffolding with no product logic. If the current date is before Oct 14 11:31 AM PDT, do only Phase P (prep) and stop.
4. Submission closes **Oct 18, 2026, 11:29 AM PDT**. Target code freeze Oct 18 06:00 PDT, final video/README by 09:00 PDT, submit by 10:00 PDT.
5. AI assistant use must be disclosed: keep `AI_DISCLOSURE.md` updated (what Claude Code generated, what the human wrote/verified).
6. The human must be able to explain every query and design decision: for each module, write a short "why" in `docs/DESIGN_NOTES.md` (3–6 lines). Prefer simple readable code over clever code.
7. Track names to declare on submit: **Agents That Act on Connected Data**, **Agent Memory and Coordination**, **Company Brain**.

**Engineering rules:**
- Python 3.11+, FastAPI, `falkordb` Python client, official `mcp` Python SDK, Anthropic SDK for agent LLM calls. Frontend: single static page with Cytoscape.js served by FastAPI (no build step).
- Verify FalkorDB syntax against current docs (https://docs.falkordb.com) before relying on any procedure name or index syntax below; fix this plan's snippets if docs differ. Never guess.
- Every Cypher query used by the product lives in `causeway/graph/queries/*.cypher` (one file per query, header comment explaining intent). Python loads them by name. This also satisfies the "include the Cypher the product depends on" submission item.
- Parameterize all Cypher. No string-formatted queries.
- Tests first for the graph layer. Run `make test` before every commit. Commit small and often with clear messages.
- Keep a running `docs/PROGRESS.md` (done / in progress / blocked / next). Update at the end of every work block.
- If a task is at risk, apply the cut list (section 9) instead of silently dropping scope.

---

## 1. Architecture

```
                ┌────────────────────────────────────────────┐
                │                 Web UI (Cytoscape)         │
                │  chat · why-path view · memory timeline    │
                └──────────────────┬─────────────────────────┘
                                   │ HTTP/SSE
                        ┌──────────▼──────────┐
                        │  FastAPI orchestrator│
                        └───┬───────┬──────┬──┘
              Triage agent  │ Root-cause   │ Comms agent
                            │ agent        │
                        ┌───▼───────▼──────▼───┐
                        │   MCP server (tools) │  ← agents pick tools via MCP
                        └──────────┬───────────┘
                                   │ Cypher / algos
                        ┌──────────▼───────────┐
                        │      FalkorDB        │
                        │ graph per tenant:    │
                        │  tenant_<id>  (KB +  │
                        │  memory + handoffs)  │
                        └──────────────────────┘
```

- **One graph per tenant** (`tenant_alpha`, `tenant_beta`). Company knowledge, memory, and handoff state all live in the tenant's graph, so isolation is structural.
- Agents never touch the DB directly; they only call MCP tools. Every tool returns `{result, evidence_paths}` where each evidence path is a list of node/edge ids.
- **Evidence rule:** the final answer is a structured object `{claims:[{text, path_ids[]}]}`. A verifier rejects any claim whose path does not exist in the graph or does not connect the entities named in the claim.

---

## 2. Graph data model

### Company-brain layer (Track 3)
Nodes: `Person{id,name,role}`, `Team{id,name}`, `Service{id,name,tier}`, `Repo{id,name}`, `Commit{id,sha,ts,msg}`, `PR{id,title,ts}`, `Test{id,name,flaky_score}`, `Ticket{id,title,status,ts}`, `Incident{id,title,sev,ts,resolved_ts}`, `Decision{id,title,ts,status}`, `Doc{id,title,kind,body,embedding}`, `Thread{id,channel,ts}`.

Edges: `(Person)-[:MEMBER_OF]->(Team)`, `(Team)-[:OWNS]->(Service)`, `(Service)-[:DEPENDS_ON]->(Service)`, `(Commit)-[:AUTHORED_BY]->(Person)`, `(Commit)-[:MODIFIED]->(Service)`, `(PR)-[:CONTAINS]->(Commit)`, `(Test)-[:COVERS]->(Service)`, `(Incident)-[:AFFECTED]->(Service)`, `(Incident)-[:CAUSED_BY]->(Commit)`, `(Ticket)-[:ABOUT]->(Incident|Service)`, `(Decision)-[:DECIDED_IN]->(Doc|Thread)`, `(Decision)-[:CONCERNS]->(Service)`, `(Person)-[:KNOWS_ABOUT {weight}]->(Service)`, `(Doc)-[:DESCRIBES]->(Service)`, `(Decision)-[:SUPERSEDES]->(Decision)`.

Temporal: every fact edge carries `valid_from`, optional `valid_to`. "Current" = `valid_to IS NULL`. Nothing is deleted; beliefs are superseded.

### Memory layer (Track 2)
- `Episode{id,ts,summary,outcome}` — one per investigation. `(Episode)-[:INVESTIGATED]->(Incident)`, `(Episode)-[:USED_TOOL]->(ToolCall)`, `(Episode)-[:CONCLUDED]->(Belief)`.
- `Belief{id,text,confidence,valid_from,valid_to}` (semantic). `(Belief)-[:ABOUT]->(Service|Test|Commit)`, `(Belief)-[:SUPERSEDES]->(Belief)`, `(Belief)-[:SUPPORTED_BY]->(Episode)`.
- `Playbook{id,name,trigger_pattern,success_count,fail_count}` (procedural). `(Playbook)-[:HAS_STEP {order}]->(PlaybookStep{tool,args_template})`. `(Episode)-[:FOLLOWED]->(Playbook)`.
- `Agent{id,role}`, `Task{id,status,kind}`, `Handoff{id,ts,payload}`. `(Agent)-[:CLAIMED]->(Task)`, `(Task)-[:HANDED_OFF_VIA]->(Handoff)-[:TO]->(Agent)`, `(Task)-[:PART_OF]->(Episode)`.

### Indexes
- Range indexes on `id` for every label; on `Incident.ts`, `Commit.ts`.
- Vector index on `Doc.embedding` and `Belief.embedding` (use a small local embedding model such as `sentence-transformers/all-MiniLM-L6-v2`, dim 384). Vector search is only an *entry point*; graph traversal does the reasoning.

---

## 3. MCP tool surface (the agents' only interface)

Implement as an MCP server (`causeway/mcp_server.py`), each tool backed by a `.cypher` file or an algorithm call:

| Tool | Purpose | Graph work |
|---|---|---|
| `find_entry_points(text)` | map a failing test/alert/text to graph nodes | vector search → node ids |
| `trace_dependencies(service, depth)` | upstream/downstream blast radius | variable-length traversal |
| `recent_changes(service, window)` | commits/PRs hitting service and its deps | multi-hop with time filter |
| `rank_suspects(incident_or_test)` | rank commits/authors | score = recency × path proximity × historical-flake × centrality (PageRank/betweenness via FalkorDB algos) |
| `similar_incidents(incident)` | past incidents with overlapping dependency subgraph | Jaccard over neighbor sets or shared-path count |
| `who_knows(service)` | owners + experts | `OWNS`, `KNOWS_ABOUT`, authorship weight |
| `decision_trace(entity)` | why was it built this way | follow `CONCERNS`←`Decision`→`DECIDED_IN`→`Doc/Thread` and `SUPERSEDES` chain |
| `recall(query)` | retrieve beliefs/episodes/playbooks | vector entry + traverse `ABOUT`/`SUPPORTED_BY` |
| `remember_episode(...)` | write episode, beliefs, playbook stats | transactional write |
| `supersede_belief(old, new, reason)` | keep history | new node + `SUPERSEDES`, set `valid_to` |
| `counterfactual(test_or_check)` | "would this have caught it?" | traversal: does a `COVERS` path exist from the check to the culprit's `MODIFIED` service |
| `open_task / claim_task / handoff(task, to_agent, payload)` | multi-agent coordination | Task/Handoff nodes with atomic claim |
| `file_ticket / propose_rollback` | actions | create `Ticket` node linked via `ABOUT`; rollback proposal as `Task` |

Every tool returns evidence path ids. Add a decorator that records each call as a `ToolCall` node linked to the current `Episode` (this is the audit trail).

---

## 4. Agents

All use the Anthropic SDK tool-use loop, tools provided via MCP client. Model name via env var `CAUSEWAY_MODEL` (don't hardcode).

1. **Triage agent** — input: a failure (test name, log excerpt, deploy id). Calls `recall` first (has this been seen / is there a matching playbook?), then `find_entry_points`, `trace_dependencies`, `recent_changes`. Output: scoped hypothesis set; opens a `Task` and hands off to root-cause.
2. **Root-cause agent** — claims the task. Runs `rank_suspects`, `similar_incidents`, `decision_trace`, `counterfactual`. If a playbook matched, follows its steps first, then verifies. Output: ranked culprits + claims with paths.
3. **Comms/Action agent** — claims the final handoff. `who_knows` → assigns owner, `file_ticket`, `propose_rollback`, drafts an incident summary where every sentence cites a path. Then calls `remember_episode` (episodic + semantic + playbook update).
4. **Verifier (non-LLM)** — deterministic code that checks every claim's path against FalkorDB; failures are fed back to the agent once for repair, then marked "unsupported" in the UI.

Orchestrator runs agents concurrently where possible (multiple investigations in parallel for the concurrency benchmark).

---

## 5. Synthetic world and ground truth

Generator `causeway/data/generate.py`, seeded (`--seed 42`), deterministic.

- Company "Northwind Payments": ~40 people, 8 teams, ~25 services with a realistic dependency DAG, ~2,000 commits, ~300 PRs, ~200 tests (some flaky), ~60 docs, ~40 decisions (some superseded), ~150 threads.
- **30 planted incidents** over a timeline, each with a known `root_cause_commit` and `root_cause_service`. Plant difficulty tiers:
  - Easy (10): culprit in the failing service itself.
  - Medium (10): culprit 2–3 hops up the dependency chain.
  - Hard (10): culprit is a config/dependency change whose symptom shows in an unrelated service; flaky tests act as decoys; some commit messages are misleading.
- **Recurring patterns:** 5 incident families that repeat (e.g., "retry-policy change × payment-gateway timeout"). Incidents in a family share structure so memory can pay off.
- **Decision story:** at least 3 decisions with `SUPERSEDES` chains so the "why do we have this retry policy" demo works and one belief is later invalidated.
- Output: Cypher/JSON load files under `data/`, plus `data/ground_truth.json`. Loader `make seed` creates `tenant_alpha` and a smaller `tenant_beta` (for isolation tests).

---

## 6. Evaluation harness (the differentiator — build it early)

`eval/run_eval.py`, results to `eval/results/*.json` and `docs/RESULTS.md` (auto-generated tables).

**Systems compared on all 30 incidents:**
- **B0** LLM only, incident text, no retrieval.
- **B1** Flat RAG: same corpus (docs/commits/tickets as text chunks), vector search only, no graph.
- **B2** Causeway graph agents, memory disabled (memory tools return empty).
- **B3** Causeway full: graph + memory, incidents run in chronological order so memory accumulates.

**Metrics:** root-cause top-1 / top-3 accuracy (by difficulty tier), path faithfulness (% claims whose path verifies), mean tool calls and tokens per incident, wall-clock time, and for B3 the **learning curve** (accuracy/steps for incident family occurrences 1st vs 2nd vs 3rd).

**Extra tests (pytest):**
- `test_path_faithfulness`: fabricated claim paths are rejected by the verifier.
- `test_tenant_isolation`: agent bound to `tenant_beta` cannot read any `tenant_alpha` node via any tool (attempt crafted cross-tenant ids and prompt injection; assert zero leakage).
- `test_concurrency`: N=50 parallel investigations plus concurrent memory writes; assert no lost writes, no duplicate task claims (each Task claimed by exactly one agent), report p50/p95 latency.
- `test_supersession`: superseding a belief preserves history and `recall` returns the current one by default.
- `test_graph_dependence` (ablation proof for Rule 3): run with the graph tools disabled and assert quality falls below B1 and the app fails health check without FalkorDB.

Be honest in results. Report where the graph does *not* help. Judges respect real numbers.

---

## 7. UI (keep it small, make it legible in a 3-minute video)

Single page, three panes:
1. **Chat/Investigation stream** — agent steps with tool calls.
2. **Why-path view** — Cytoscape graph; click any claim in the answer → highlights its path in the graph.
3. **Memory timeline** — episodes, beliefs (with supersession), playbook success counts; a toggle to show "memory off vs on" for the same incident.

Plus a header strip: tenant switcher, incident picker, latency/tool-call counters.

---

## 8. Schedule (PDT) and tasks with acceptance criteria

### Phase P — Prep (allowed now through Oct 14 11:30 AM; NO product logic)
- P1. Repo scaffold: `README.md` stub, `Makefile`, `docker-compose.yml` (FalkorDB + browser), `pyproject.toml`, folder layout, `AI_DISCLOSURE.md`, `docs/PROGRESS.md`, `docs/DESIGN_NOTES.md`.
- P2. Write `docs/GRAPH_MODEL.md` (from section 2) with a diagram; draft `docs/QUERIES_DRAFT.md` (Cypher drafts for each MCP tool). Drafts only.
- P3. Write the synthetic-world story bible `docs/WORLD.md`: teams, services, DAG, the 30 incidents (tier, family, culprit) in prose/table. No generator code yet.
- P4. Write `docs/EVAL_SPEC.md` (metrics, baselines, test list). Pick the embedding model and verify it runs offline.
- P5. Draft the demo script (`docs/DEMO_SCRIPT.md`, 3 min, shot list).
- *Gate:* human reviews and understands the model, since they must explain it.

### Day 1 — Oct 14 (start 11:31 AM): Foundation
- 1.1 `docker compose up` FalkorDB; Python client smoke test. *AC: create/read a node in a named graph.*
- 1.2 Schema + indexes creation script. *AC: idempotent `make schema`; vector index works.*
- 1.3 World generator + `make seed` for two tenants. *AC: counts match spec; ground_truth.json produced; deterministic by seed.*
- 1.4 Query library (`.cypher` files) for read tools + unit tests against seeded data. *AC: each query has a test with an expected result derived from ground truth.*
- 1.5 Eval harness skeleton + B0/B1 baselines running on all 30 incidents. *AC: `make eval-baselines` outputs a table.*
- *Day-1 exit:* graph loaded, baselines scored, nothing agentic yet.

### Day 2 — Oct 15: Tools + Track 3 + Track 1
- 2.1 MCP server with read tools (`find_entry_points`, `trace_dependencies`, `recent_changes`, `who_knows`, `decision_trace`, `similar_incidents`, `rank_suspects`) with evidence paths and `ToolCall` auditing.
- 2.2 Verifier + `test_path_faithfulness`.
- 2.3 Single combined agent loop (triage+root-cause in one) over MCP. *AC: B2 runs on all 30; report top-1/top-3.*
- 2.4 Company-brain Q&A mode: "who owns X", "why did we choose Y" with cited paths. *AC: 10 scripted questions all verify.*
- 2.5 `counterfactual` tool and action tools (`file_ticket`, `propose_rollback`).
- *Day-2 exit:* B2 numbers exist; Track 1 and 3 are demonstrable.

### Day 3 — Oct 16: Track 2 memory + coordination
- 3.1 Memory write path (`remember_episode`, beliefs, playbooks) and read path (`recall`). *AC: after incident N, `recall` surfaces it for a same-family incident.*
- 3.2 `supersede_belief` + temporal validity + `test_supersession`.
- 3.3 Split into three agents with Task/Handoff nodes and atomic claim. *AC: `test_concurrency` passes.*
- 3.4 B3 run in chronological order; produce learning curve. *AC: results table shows B3 vs B2 and per-family improvement.*
- 3.5 Tenant isolation enforcement (tenant bound at MCP session level, not by prompt) + `test_tenant_isolation`.
- *Day-3 exit:* all three tracks functionally complete, with numbers.

### Day 4 — Oct 17: UI, polish, deployment
- 4.1 UI three-pane page; why-path highlight; memory timeline; memory on/off toggle.
- 4.2 Fix the worst eval failures (look at hard-tier misses; improve `rank_suspects` weights and prompts, not the ground truth).
- 4.3 Deploy: container image + hosted FalkorDB (FalkorDB Cloud or a VM). If deploy fails by 8 PM, ship complete local setup instructions and a recorded run.
- 4.4 Run the full eval, auto-generate `docs/RESULTS.md`.
- 4.5 Draft README (sections in 10).

### Day 5 — Oct 18 (until 11:29 AM): Ship
- 5.1 Code freeze 06:00. Only bug fixes after.
- 5.2 Record demo video from `docs/DEMO_SCRIPT.md` (≤3 min; record early, re-record only if broken).
- 5.3 Final README, `AI_DISCLOSURE.md`, make repo public, verify a clean clone runs via `make demo`.
- 5.4 Submit by 10:00 selecting all three tracks. Leave 90 minutes of slack.

---

## 9. Cut list (apply in this order if behind)
1. Deployment → local setup instructions plus recorded demo.
2. UI memory timeline → static table.
3. Comms agent drafting → ticket creation only.
4. `counterfactual` tool.
5. Hard-tier incidents reduced from 10 to 5.
6. Never cut: verifier, graph-vs-baseline ablation, tenant isolation, memory write/recall, README graph model + Cypher list.

---

## 10. Required submission artifacts checklist
- [ ] Public repo
- [ ] README: pitch, architecture diagram, **graph data model**, setup (`make demo`), list of Cypher queries/algorithms with file links, results table, track declarations, AI-use disclosure link
- [ ] `causeway/graph/queries/*.cypher` (the queries the product depends on)
- [ ] Demo video (≤3 min): hook → live investigation with why-path → same-family incident resolved faster with memory → ablation numbers → isolation/concurrency proof
- [ ] Live deployment or complete local setup
- [ ] Tracks named: Agents That Act on Connected Data, Agent Memory and Coordination, Company Brain
- [ ] `AI_DISCLOSURE.md`
- [ ] Human can explain: graph model, `rank_suspects` scoring, supersession logic, tenant binding, why graph beats baseline (or where it doesn't)

---

## 11. Repo layout
```
causeway/
  CLAUDE.md  PLAN.md  README.md  AI_DISCLOSURE.md  Makefile  docker-compose.yml
  causeway/
    graph/ (client.py, schema.py, queries/*.cypher, verifier.py)
    data/  (generate.py, loader.py)
    mcp_server.py
    agents/ (triage.py, rootcause.py, comms.py, orchestrator.py, prompts/)
    memory/ (write.py, recall.py)
    api/   (main.py, static/index.html)
  eval/ (run_eval.py, baselines.py, results/)
  tests/
  docs/ (GRAPH_MODEL.md, WORLD.md, EVAL_SPEC.md, DESIGN_NOTES.md, PROGRESS.md, DEMO_SCRIPT.md, RESULTS.md)
```

## 12. Kickoff prompt to paste into Claude Code
> Read PLAN.md fully. Check today's date and time. If it is before Oct 14, 2026 11:31 AM PDT, do only Phase P (docs, scaffolding, drafts; no product logic) and stop. Otherwise continue from the first unfinished task in docs/PROGRESS.md. Work task by task, honor every acceptance criterion, run `make test` before each commit, update docs/PROGRESS.md and docs/DESIGN_NOTES.md after each task, and ask me before changing the graph model or dropping scope. Verify all FalkorDB syntax against current docs.
