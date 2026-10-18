import asyncio

from causeway import mcp_server
from causeway.session import Session

TOOLS = {"find_entry_points", "trace_dependencies", "recent_changes", "rank_suspects", "similar_incidents",
         "who_knows", "decision_trace", "recall", "remember_episode"}


def test_all_tools_are_registered_and_take_no_tenant():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    assert {t.name for t in tools} == TOOLS
    assert all("tenant" not in t.inputSchema.get("properties", {}) for t in tools)


def test_tool_call_returns_result_and_evidence(graph, monkeypatch):
    monkeypatch.setattr(mcp_server, "_session", Session("alpha", graph))
    out = asyncio.run(mcp_server.mcp.call_tool("who_knows", {"service": "svc-ledger"}))
    text = str(out)
    assert "evidence_paths" in text and "svc-ledger" in text
