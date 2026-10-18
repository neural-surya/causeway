"""Compare three systems on all incidents:  python -m eval.run_eval

  flat_rag    no graph: embed the alert text, rank every commit in the 72h before the incident by text similarity
  graph       graph candidates (dependency-aware) ranked by rank_suspects, no memory
  graph+mem   same, plus memory: incidents run in chronological order; each resolved incident is written back
              (remember_episode) and later incidents use recalled culprit commit messages as exemplars

Scores against data/ground_truth.json. Results: eval/results/results.json and docs/RESULTS.md.
"""
import json
import time
from collections import defaultdict
from pathlib import Path

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA
from causeway.embed import embed
from causeway.graph.client import get_db
from causeway.graph.queries import run
from causeway.session import Session

ROOT = Path(__file__).resolve().parent.parent


def flat_rag(session, truth):
    [ctx] = run(session.graph, "incident_context", incident=truth["incident"])
    q = embed(ctx["summary"])
    rows = run(session.graph, "all_commits_window", as_of=ctx["ts"], window_hours=72)
    scored = sorted(rows, key=lambda r: -sum(a * b for a, b in zip(q, embed(r["msg"]))))
    return [r["commit"] for r in scored], None


def graph_system(session, truth, exemplars=None):
    ranked = session.rank_suspects(truth["incident"], exemplars)
    top = ranked[0] if ranked else None
    claim = None
    if top:
        claim = dict(text=f"{top['commit']} is the likely root cause", path_ids=top["path_ids"][:-1],
                     entities=[truth["failing_service"], top["commit"]])
    return [r["commit"] for r in ranked], claim


def evaluate():
    world = generate(ALPHA, 42)
    incidents = sorted(world.truth["incidents"], key=lambda t: t["ts"])
    db = get_db()
    results = {}
    for system in ("flat_rag", "graph", "graph+mem"):
        g = db.select_graph(f"eval_{system.replace('+', '_')}")
        load_world(g, world)
        s = Session("alpha", g)
        rows = []
        for t in incidents:
            t0 = time.perf_counter()
            if system == "flat_rag":
                ranking, claim = flat_rag(s, t)
            elif system == "graph":
                ranking, claim = graph_system(s, t)
            else:
                ex = [b["commit_msg"] for b in s.recall(as_of=t["ts"])]
                ranking, claim = graph_system(s, t, ex)
            ms = (time.perf_counter() - t0) * 1000
            verified = None if claim is None else s.verify(claim).ok
            rows.append(dict(incident=t["incident"], tier=t["tier"], family=t["family"], occurrence=t["occurrence"],
                             top1=bool(ranking) and ranking[0] == t["root_cause_commit"],
                             top3=t["root_cause_commit"] in ranking[:3],
                             rank=(ranking.index(t["root_cause_commit"]) + 1) if t["root_cause_commit"] in ranking else None,
                             candidates=len(ranking), claim_verified=verified, ms=round(ms, 1)))
            if system == "graph+mem":  # incident resolved: the team confirms the culprit, memory learns it
                s.remember_episode(incident=t["incident"], culprit_commit=t["root_cause_commit"],
                                   summary=next(c["msg"] for c in world.nodes["Commit"] if c["id"] == t["root_cause_commit"]),
                                   ts=t["ts"] + 3600)
        g.delete()
        results[system] = rows
    return results


def rate(rows, key):
    return round(100 * sum(r[key] for r in rows) / len(rows)) if rows else None


def table(results):
    out = ["| system | top-1 | top-3 | easy top-1 | medium top-1 | hard top-1 | verified claims | mean ms |",
           "|---|---|---|---|---|---|---|---|"]
    for system, rows in results.items():
        by = lambda tier: [r for r in rows if r["tier"] == tier]
        v = [r["claim_verified"] for r in rows if r["claim_verified"] is not None]
        out.append(f"| {system} | {rate(rows,'top1')}% | {rate(rows,'top3')}% | {rate(by('easy'),'top1')}% | "
                   f"{rate(by('medium'),'top1')}% | {rate(by('hard'),'top1')}% | "
                   f"{'n/a (no graph path)' if not v else f'{round(100*sum(v)/len(v))}%'} | "
                   f"{round(sum(r['ms'] for r in rows)/len(rows), 1)} |")
    out += ["", "Learning curve (top-1 by how many times the incident family has occurred before):", "",
            "| system | 1st occurrence | 2nd | 3rd |", "|---|---|---|---|"]
    for system, rows in results.items():
        cells = [f"{rate([r for r in rows if r['occurrence'] == o], 'top1')}%" for o in (1, 2, 3)]
        out.append(f"| {system} | " + " | ".join(cells) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    res = evaluate()
    (ROOT / "eval/results").mkdir(parents=True, exist_ok=True)
    (ROOT / "eval/results/results.json").write_text(json.dumps(res, indent=1))
    md = ("# Results\n\nAuto-generated by `make eval` (12 incidents, 4 families x 3, seed 42). "
          "Chance level is 1 in the candidate count shown in results.json.\n\n" + table(res) + "\n")
    (ROOT / "docs/RESULTS.md").write_text(md)
    print(table(res))
