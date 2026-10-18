"""rank_suspects: score candidate commits using graph signals (no LLM, fully explainable).

candidates come from the `recent_changes` query (service + dependencies, bounded by the incident time):
    score = recency * proximity * centrality * risk  [* memory boost]
  recency    = 0.5 ** (age_hours / 24)           newer change => more suspicious
  proximity  = 1 / (1 + hops)                    closer in the dependency graph => more suspicious
  centrality = 1 + log(1 + dependents)           a change to a widely used service has a bigger blast radius
  risk       = 2 if the message mentions a risky word (retry, timeout, schema, config, default, column...)
Memory boost (only when memory is on): past culprit commits of resolved incidents are used as
exemplars; a candidate whose message is similar to an exemplar (cosine, via the embedding) is boosted.
"""
import math

from causeway.embed import embed
from causeway.graph.queries import run

RISKY = ("retry", "timeout", "schema", "config", "default", "column", "migrat", "rename", "drop")


def _dot(u, v):
    return sum(x * y for x, y in zip(u, v))


def rank_suspects(graph, incident: str, exemplars: list[str] | None = None,
                  window_hours: int = 72, depth: int = 3) -> list[dict]:
    [ctx] = run(graph, "incident_context", incident=incident)
    cands = run(graph, "recent_changes", service=ctx["service_id"], depth=depth,
                as_of=ctx["ts"], window_hours=window_hours)
    dependents = {r["service"]: r["dependents"] for r in run(graph, "service_features")}
    ex_vecs = [embed(m) for m in (exemplars or [])]
    out = []
    for c in cands:
        age_h = (ctx["ts"] - c["ts"]) / 3600
        recency = 0.5 ** (age_h / 24)
        proximity = 1 / (1 + c["hops"])
        centrality = 1 + math.log(1 + dependents[c["service"]])
        risk = 2.0 if any(w in c["msg"].lower() for w in RISKY) else 1.0
        memory = 1.0
        if ex_vecs:
            sim = max(_dot(embed(c["msg"]), v) for v in ex_vecs)
            memory = 1 + 20 * max(0.0, sim - 0.5)  # only clearly similar messages get a boost
        score = recency * proximity * centrality * risk * memory
        out.append(dict(c, score=score, memory=memory,
                        incident_service=ctx["service_id"]))
    return sorted(out, key=lambda r: -r["score"])
