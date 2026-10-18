"""Two cooperating agents over the graph, coordinating through Task/Handoff nodes.

  triage      opens a Task, gathers scope (entry points, dependencies, recent changes, recalled memory),
              hands the Task off to root-cause with a payload
  root-cause  atomically claims the Task, ranks suspects, looks up similar incidents / owners /
              decisions, and produces claims; every claim is checked by the deterministic verifier

These agents are deterministic code (no LLM calls): the reasoning is the graph queries and the scoring in
ranking.py. Each tool call is recorded in `steps` so the UI can replay it.
"""
import uuid

from causeway.graph.queries import run
from causeway.tasks import claim_task, handoff, open_task


def _step(steps, agent, tool, args, summary):
    steps.append(dict(agent=agent, tool=tool, args=args, summary=summary))


def investigate(s, incident: str, use_memory: bool = True) -> dict:
    steps, g = [], s.graph
    [ctx] = run(g, "incident_context", incident=incident)
    svc, ts = ctx["service_id"], ctx["ts"]
    uid = uuid.uuid4().hex[:8]
    task, ep = f"task-{incident}-{uid}", f"ep-{incident}"

    # ---- triage agent
    open_task(g, task, ep, incident, "agent-triage", "triage", "root_cause", ts)
    _step(steps, "triage", "open_task", {"incident": incident}, f"opened {task}")
    entry = s.find_entry_points(ctx["summary"], k=6)
    _step(steps, "triage", "find_entry_points", {"text": ctx["summary"][:60] + "..."},
          "services matched by runbook search: " + ", ".join(list(dict.fromkeys(r["service"] for r in entry))[:3]))
    deps = s.trace_dependencies(svc, 3)
    _step(steps, "triage", "trace_dependencies", {"service": svc, "depth": 3},
          f"{svc} depends on {len({d['dependency'] for d in deps})} services within 3 hops")
    changes = s.recent_changes(svc, ts)
    _step(steps, "triage", "recent_changes", {"service": svc, "window_hours": 72},
          f"{len(changes)} commits touched {svc} or its dependencies in the 72h before the incident")
    exemplars = []
    if use_memory:
        recalled = s.recall(as_of=ts)
        exemplars = [b["commit_msg"] for b in recalled]
        _step(steps, "triage", "recall", {"as_of": ts},
              f"{len(recalled)} past root-cause belief(s) recalled" + (f", e.g. '{recalled[0]['commit_msg']}'" if recalled else ""))
    handoff(g, task, f"h-{task}", "agent-rootcause", "root_cause",
            dict(service=svc, candidates=len(changes), exemplars=len(exemplars)), ts)
    _step(steps, "triage", "handoff", {"to": "root-cause"}, "handed the task to root-cause with scoped candidates")

    # ---- root-cause agent
    payload = claim_task(g, task, "agent-rootcause")
    _step(steps, "root-cause", "claim_task", {"task": task}, "claimed the task atomically" if payload else "claim lost")
    ranked = s.rank_suspects(incident, exemplars)
    top = ranked[:5]
    _step(steps, "root-cause", "rank_suspects", {"incident": incident},
          "top suspect " + (f"{top[0]['commit']} ({top[0]['msg']})" if top else "none"))
    sim = s.similar_incidents(incident)
    _step(steps, "root-cause", "similar_incidents", {"incident": incident},
          f"{len(sim)} earlier incident(s) with overlapping dependency neighbourhood")
    culprit_service = top[0]["service"] if top else svc
    owners = s.who_knows(culprit_service)
    _step(steps, "root-cause", "who_knows", {"service": culprit_service},
          f"{len({o['person'] for o in owners})} people own or know {culprit_service}")
    decisions = s.decision_trace(culprit_service)
    _step(steps, "root-cause", "decision_trace", {"service": culprit_service},
          f"{len(decisions)} decision(s) concern {culprit_service}")

    claims = []
    for r in top[:3]:
        c = dict(text=f"{r['commit']} ('{r['msg']}') may have caused the failure in {svc}",
                 path_ids=r["path_ids"][:-1], entities=[svc, r["commit"]])
        v = s.verify(c)
        claims.append(dict(c, verified=v.ok, reason=v.reason, score=round(r["score"], 4)))
    _step(steps, "root-cause", "verify", {"claims": len(claims)},
          f"{sum(c['verified'] for c in claims)}/{len(claims)} claims verified against the graph")
    return dict(incident=incident, summary=ctx["summary"], service=svc, task=task, steps=steps,
                suspects=[dict(commit=r["commit"], msg=r["msg"], service=r["service"], hops=r["hops"],
                               score=round(r["score"], 4), memory_boost=round(r["memory"], 2)) for r in top],
                claims=claims, elements=graph_elements(g, [c["path_ids"] for c in claims]))


def graph_elements(g, paths) -> dict:
    """Cytoscape nodes/edges for the claim paths."""
    nodes, edges = {}, {}
    for pi, path in enumerate(paths):
        for nid in path:
            if nid not in nodes:
                nodes[nid] = (run(g, "node_info", id=nid) or [dict(id=nid, label="?", name=nid)])[0]
        for a, b in zip(path, path[1:]):
            rel = run(g, "edge_between", a=a, b=b)
            if rel:
                src, dst = (a, b) if rel[0]["forward"] else (b, a)
                edges[f"{src}>{dst}"] = dict(id=f"{src}>{dst}", source=src, target=dst, label=rel[0]["rel"])
    return dict(nodes=[dict(data=n) for n in nodes.values()], edges=[dict(data=e) for e in edges.values()])


def resolve(s, incident: str, culprit_commit: str, summary: str, ts: int):
    """The team confirms the root cause; memory learns it."""
    return s.remember_episode(incident=incident, culprit_commit=culprit_commit, summary=summary, ts=ts)
