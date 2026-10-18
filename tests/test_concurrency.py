"""Concurrent investigations: no duplicate claims, no lost writes. Reports p50/p95 latency."""
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA
from causeway.graph.client import get_db
from causeway.memory import recall, remember_episode
from causeway.tasks import claim_task, handoff, open_task


@pytest.fixture
def env():
    g = get_db().select_graph("concurrency_test_alpha")
    w = generate(ALPHA, 42)
    load_world(g, w)
    yield g, w.truth["incidents"]
    g.delete()


def timed(fn, *a, **k):
    t0 = time.perf_counter()
    out = fn(*a, **k)
    return out, (time.perf_counter() - t0) * 1000


def test_a_task_is_claimed_by_exactly_one_of_many_racers(env):
    g, _ = env
    open_task(g, "task-x", "ep-x", "inc-01", "agent-triage", "triage", "root_cause", 1)
    handoff(g, "task-x", "h-x", "agent-rootcause", "root_cause", {"suspects": ["com-001"]}, 2)
    with ThreadPoolExecutor(20) as ex:
        results = list(ex.map(lambda _: claim_task(g, "task-x", "agent-rootcause"), range(20)))
    winners = [r for r in results if r is not None]
    assert len(winners) == 1 and winners[0] == {"suspects": ["com-001"]}
    n = g.ro_query("MATCH (:Agent)-[c:CLAIMED]->(:Task {id: 'task-x'}) RETURN count(c)").result_set[0][0]
    assert n == 1


def test_cannot_claim_a_task_not_handed_to_you(env):
    g, _ = env
    open_task(g, "task-y", "ep-y", "inc-01", "agent-triage", "triage", "root_cause", 1)
    assert claim_task(g, "task-y", "agent-rootcause") is None      # not handed off yet
    handoff(g, "task-y", "h-y", "agent-rootcause", "root_cause", {}, 2)
    assert claim_task(g, "task-y", "agent-someone-else") is None   # handed to a different agent


def test_50_parallel_investigations_with_memory_writes(env):
    g, incidents = env
    def investigation(i):
        t = incidents[i % len(incidents)]
        task = f"task-{i:03d}"
        _, a = timed(open_task, g, task, f"ep-{t['incident']}", t["incident"], "agent-triage", "triage", "root_cause", i)
        _, b = timed(handoff, g, task, f"h-{i:03d}", "agent-rootcause", "root_cause", {"i": i}, i)
        won, c = timed(claim_task, g, task, "agent-rootcause")
        _, d = timed(remember_episode, g, t["incident"], t["root_cause_commit"], "m", t["ts"] + 10)
        return won, [a, b, c, d]
    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(investigation, range(50)))
    assert all(won == {"i": i} for i, (won, _) in enumerate(out))             # every task claimed once
    count = lambda q: g.ro_query(q).result_set[0][0]
    assert count("MATCH (t:Task) RETURN count(t)") == 50                       # no lost writes
    assert count("MATCH (:Agent)-[c:CLAIMED]->(:Task) RETURN count(c)") == 50  # no duplicate claims
    assert count("MATCH (e:Episode) RETURN count(e)") == 12                    # MERGE: no duplicate episodes
    assert count("MATCH (b:Belief) RETURN count(b)") == 12
    assert len(recall(g, as_of=10**12)) == 12
    lat = sorted(ms for _, calls in out for ms in calls)
    print(f"\nlatency per call over {len(lat)} calls: p50={statistics.median(lat):.1f}ms "
          f"p95={lat[int(len(lat) * 0.95)]:.1f}ms")
