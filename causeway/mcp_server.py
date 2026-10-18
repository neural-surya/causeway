"""MCP server: the agents' tool surface.   python -m causeway.mcp_server   (stdio)

The tenant is fixed by the CAUSEWAY_TENANT environment variable when the server starts (default alpha).
No tool takes a tenant argument, so neither the model nor a prompt can switch tenants.
Every tool returns {"result": ..., "evidence_paths": [[node ids], ...]}.
"""
import os

from mcp.server.fastmcp import FastMCP

from causeway.session import Session

mcp = FastMCP("causeway")
_session: Session | None = None


def session() -> Session:
    global _session
    if _session is None:
        _session = Session(os.environ.get("CAUSEWAY_TENANT", "alpha"))
    return _session


def _out(rows, paths=None):
    paths = paths if paths is not None else [r["path_ids"] for r in rows if isinstance(r, dict) and "path_ids" in r]
    return {"result": rows, "evidence_paths": paths}


@mcp.tool()
def find_entry_points(text: str, k: int = 6) -> dict:
    """Map an alert, log line or failing test name to services in the graph."""
    return _out(session().find_entry_points(text, k))


@mcp.tool()
def trace_dependencies(service: str, depth: int = 3) -> dict:
    """What a service depends on (blast radius), up to `depth` hops."""
    return _out(session().trace_dependencies(service, depth))


@mcp.tool()
def recent_changes(service: str, as_of: int, window_hours: int = 72) -> dict:
    """Commits touching the service or its dependencies in the window before `as_of` (epoch seconds)."""
    return _out(session().recent_changes(service, as_of, window_hours))


@mcp.tool()
def rank_suspects(incident: str, use_memory: bool = True) -> dict:
    """Rank suspect commits for an incident (recency x proximity x centrality x risk, plus memory boost)."""
    s = session()
    ex = [b["commit_msg"] for b in s.recall(as_of=_incident_ts(incident))] if use_memory else []
    return _out(s.rank_suspects(incident, ex))


def _incident_ts(incident: str) -> int:
    from causeway.graph.queries import run
    return run(session().graph, "incident_context", incident=incident)[0]["ts"]


@mcp.tool()
def similar_incidents(incident: str) -> dict:
    """Earlier incidents whose dependency neighbourhood overlaps this one's (Jaccard)."""
    return _out(session().similar_incidents(incident), [])


@mcp.tool()
def who_knows(service: str) -> dict:
    """Owners and experts for a service."""
    return _out(session().who_knows(service))


@mcp.tool()
def decision_trace(service: str) -> dict:
    """Why a service is built the way it is: decisions, their documents and supersession chain."""
    return _out(session().decision_trace(service))


@mcp.tool()
def recall(as_of: int, include_history: bool = False) -> dict:
    """Recall past root-cause beliefs (current by default) known before `as_of`."""
    return _out(session().recall(as_of, include_history))


@mcp.tool()
def remember_episode(incident: str, culprit_commit: str, summary: str, ts: int) -> dict:
    """Record a resolved investigation: episode, belief and the confirmed root cause."""
    return _out(session().remember_episode(incident=incident, culprit_commit=culprit_commit, summary=summary, ts=ts), [])


if __name__ == "__main__":
    mcp.run()
