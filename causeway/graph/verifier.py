"""Deterministic (non-LLM) claim verifier.

A claim is {"text": str, "path_ids": [id, ...], "entities": [id, ...]}.
It is supported only if
  1. the path has at least two nodes,
  2. every consecutive pair of ids is joined by a real relationship in the graph, and
  3. every entity the claim names appears in the path.
Anything else is "unsupported" with a reason. Agents cannot talk their way past this:
it only asks FalkorDB whether the edges exist.
"""
from dataclasses import dataclass

from falkordb import Graph

from causeway.graph.queries import run


@dataclass
class Verdict:
    ok: bool
    reason: str = ""


def verify_claim(graph: Graph, claim: dict) -> Verdict:
    path = claim.get("path_ids") or []
    if len(path) < 2:
        return Verdict(False, "path needs at least two nodes")
    for a, b in zip(path, path[1:]):
        if not run(graph, "edge_between", a=a, b=b):
            return Verdict(False, f"no relationship between {a} and {b}")
    missing = [e for e in claim.get("entities", []) if e not in path]
    if missing:
        return Verdict(False, f"path does not mention {', '.join(missing)}")
    return Verdict(True)


def verify_answer(graph: Graph, claims: list[dict]) -> dict:
    """Verify every claim; faithfulness = share of claims that verified."""
    verdicts = [verify_claim(graph, c) for c in claims]
    return dict(
        faithfulness=(sum(v.ok for v in verdicts) / len(verdicts)) if verdicts else 1.0,
        verdicts=verdicts,
    )
