"""Agent memory in the graph: episodes (what happened), beliefs (what we concluded), supersession."""
from causeway.embed import embed
from causeway.graph.queries import run, write


def remember_episode(graph, incident: str, culprit_commit: str, summary: str, ts: int, confidence: float = 0.8):
    text = f"Root cause of {incident} was commit {culprit_commit}: {summary}"
    return write(graph, "remember_episode", incident=incident, commit=culprit_commit, summary=summary, ts=ts,
                 episode=f"ep-{incident}", belief=f"bel-{incident}", text=text, confidence=confidence,
                 emb=embed(text))


def recall(graph, as_of: int, include_history: bool = False) -> list[dict]:
    return run(graph, "recall", as_of=as_of, include_history=include_history)


def supersede_belief(graph, old: str, new: str, text: str, reason: str, ts: int, confidence: float = 0.8):
    return write(graph, "supersede_belief", old=old, new=new, text=text, reason=reason, ts=ts,
                 confidence=confidence, emb=embed(text))
