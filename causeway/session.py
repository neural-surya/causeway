"""Tenant-bound session. The tenant is fixed when the session is created, in code, and no tool
accepts a tenant argument, so neither crafted ids nor prompt text can reach another tenant's graph."""
from causeway import memory
from causeway.embed import embed
from causeway.graph.client import get_db
from causeway.graph.queries import run
from causeway.graph.verifier import verify_claim
from causeway.ranking import rank_suspects


class Session:
    def __init__(self, tenant: str, graph=None):
        self.tenant = tenant
        self.graph = graph or get_db().select_graph(f"tenant_{tenant}")

    # read tools
    def find_entry_points(self, text, k=6):
        return run(self.graph, "entry_points", q=embed(text), k=k)

    def trace_dependencies(self, service, depth=3):
        return run(self.graph, "trace_dependencies", service=service, depth=depth)

    def recent_changes(self, service, as_of, window_hours=72, depth=3):
        return run(self.graph, "recent_changes", service=service, as_of=as_of, window_hours=window_hours, depth=depth)

    def rank_suspects(self, incident, exemplars=None):
        return rank_suspects(self.graph, incident, exemplars)

    def similar_incidents(self, incident):
        return run(self.graph, "similar_incidents", incident=incident)

    def who_knows(self, service):
        return run(self.graph, "who_knows", service=service)

    def decision_trace(self, service):
        return run(self.graph, "decision_trace", service=service)

    def verify(self, claim):
        return verify_claim(self.graph, claim)

    # memory tools
    def recall(self, as_of, include_history=False):
        return memory.recall(self.graph, as_of, include_history)

    def remember_episode(self, **kw):
        return memory.remember_episode(self.graph, **kw)
