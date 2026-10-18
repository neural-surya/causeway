"""Seeded, deterministic synthetic company generator.

    python -m causeway.data.generate --seed 42 --out data

Produces per tenant: <out>/<tenant>.json (nodes + edges) and
<out>/ground_truth[_<tenant>].json (answers for the eval; never loaded into the graph).
Time is anchored to a fixed END date, never now(), so output depends only on the seed.
"""
import argparse
import hashlib
import json
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from causeway.data.specs import ALPHA, BETA, Family, Spec

END = int(datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp())
DAY, HOUR = 86400, 3600

NOISE_MSGS = [
    "refactor: simplify {s} request handler", "fix: handle empty payload in {s}",
    "chore: bump logging in {s}", "feat: add metrics to {s}", "test: add coverage for {s} edge cases",
    "docs: update {s} runbook", "perf: cache lookups in {s}", "fix: typo in {s} error message",
    "chore: upgrade dependencies in {s}", "refactor: extract helper in {s}",
]
# culprit messages: clear for easy, plain for medium, deliberately misleading for hard
CULPRIT_MSG = {
    "retry": "feat: retry failed calls up to 5 times with no backoff in {s}",
    "schema": "refactor: drop legacy column and rename fields in {s} schema",
    "config": "chore: tidy default settings in {s}",
    "flaky": "fix: tighten input validation in {s}",
}
DECOY_MSGS = ["fix: increase timeout handling in {s}", "revert: retry tweak in {s}",
              "fix: stabilise flaky checks in {s}"]
SYMPTOM = {
    "retry": "Elevated timeouts and duplicate requests in {f}; {t} is failing",
    "schema": "5xx errors in {f}: unexpected null field returned by an upstream service; {t} is failing",
    "config": "Latency regression in {f} after the last deploy, nothing suspicious changed in {f}; {t} is failing",
    "flaky": "Release blocked: {t} is red in {f}, it has failed intermittently before",
}
TEST_NAMES = ["happy_path", "timeouts", "idempotency", "auth_failure", "bulk_load"]


@dataclass
class World:
    spec: Spec
    seed: int
    nodes: dict[str, list[dict]] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    truth: dict = field(default_factory=dict)

    def add(self, label: str, **props):
        self.nodes.setdefault(label, []).append(props)

    def link(self, sl, sid, rel, dl, did, **props):
        self.edges.append(dict(src=[sl, sid], rel=rel, dst=[dl, did], props=props))


def dependency_path(deps, src, dst):
    """Shortest DEPENDS_ON path from src to dst as a service-name list, or None."""
    adj = {}
    for a, b in deps:
        adj.setdefault(a, []).append(b)
    prev, q = {src: None}, deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        for nxt in sorted(adj.get(cur, [])):
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    return None


def _sha(seed, n):
    return hashlib.sha1(f"{seed}:{n}".encode()).hexdigest()[:10]


def generate(spec: Spec, seed: int = 42) -> World:
    rng = random.Random(f"{seed}:{spec.tenant}")
    w = World(spec, seed)
    sid = lambda s: f"svc-{s}"
    start = END - 180 * DAY

    # --- teams, people, services -------------------------------------------------
    owner_team = {s: t for t, svcs in spec.teams.items() for s in svcs}
    for t in spec.teams:
        w.add("Team", id=f"team-{t}", name=t)
    members = {t: [] for t in spec.teams}
    for i, name in enumerate(spec.people):
        team = list(spec.teams)[i % len(spec.teams)]
        role = "manager" if not members[team] else rng.choice(["engineer", "senior engineer", "staff engineer"])
        members[team].append(f"person-{i + 1:02d}")
        w.add("Person", id=f"person-{i + 1:02d}", name=name, role=role)
        w.link("Person", f"person-{i + 1:02d}", "MEMBER_OF", "Team", f"team-{team}", valid_from=start - 200 * DAY)
    for s, tier in spec.services.items():
        w.add("Service", id=sid(s), name=s, tier=tier)
        w.link("Team", f"team-{owner_team[s]}", "OWNS", "Service", sid(s), valid_from=start - 200 * DAY)
    for a, b in spec.deps:
        w.link("Service", sid(a), "DEPENDS_ON", "Service", sid(b), valid_from=start - 200 * DAY)

    # --- tests --------------------------------------------------------------------
    tests_by_svc = {}
    n = 0
    for s in spec.services:
        for name in rng.sample(TEST_NAMES, 3):
            n += 1
            flaky = round(rng.uniform(0.3, 0.6), 2) if rng.random() < 0.2 else round(rng.uniform(0, 0.05), 2)
            tid = f"test-{n:03d}"
            w.add("Test", id=tid, name=f"test_{s.replace('-', '_')}_{name}", flaky_score=flaky)
            w.link("Test", tid, "COVERS", "Service", sid(s), valid_from=start)
            tests_by_svc.setdefault(s, []).append(tid)
    test_props = {t["id"]: t for t in w.nodes["Test"]}

    # --- incident schedule (families interleaved so recurrences are spread out) ------
    plan = []
    for occ in range(max(len(f.occurrences) for f in spec.families)):
        for fam in spec.families:
            if occ < len(fam.occurrences):
                plan.append((fam, occ))
    spacing = 150 // len(plan)
    commits = []          # dicts with temporary 'key'

    def person_for(service, other_team_chance=0.15):
        team = owner_team[service]
        if rng.random() < other_team_chance:
            team = rng.choice(list(spec.teams))
        return rng.choice(members[team])

    truth_incidents = []
    for i, (fam, occ) in enumerate(plan):
        failing, culprit = fam.occurrences[occ]
        ts = END - (165 - i * spacing + rng.randint(-2, 2)) * DAY + rng.randint(0, 8) * HOUR
        iid = f"inc-{i + 1:02d}"
        c_ts = ts - rng.randint(8, 40) * HOUR
        commits.append(dict(key=f"{iid}:culprit", service=culprit, ts=c_ts, special=True,
                            msg=CULPRIT_MSG[fam.key].format(s=culprit), author=person_for(culprit, 0)))
        n_decoys = {"easy": 0, "medium": 1, "hard": 2}[fam.tier]
        for d in range(n_decoys):  # innocent, more recent, alarming wording: recency alone misleads
            commits.append(dict(key=f"{iid}:decoy{d}", service=failing, ts=ts - rng.randint(1, 6) * HOUR,
                                special=True, msg=DECOY_MSGS[d].format(s=failing), author=person_for(failing)))
        # failing test: the most flaky test in the failing service for the flaky family, else a stable one
        pool = sorted(tests_by_svc[failing], key=lambda t: test_props[t]["flaky_score"])
        failing_test = pool[-1] if fam.key == "flaky" else pool[0]
        if fam.key == "flaky":
            test_props[failing_test]["flaky_score"] = max(test_props[failing_test]["flaky_score"], 0.55)
        tname = test_props[failing_test]["name"]
        summary = SYMPTOM[fam.key].format(f=failing, t=tname)
        w.add("Incident", id=iid, title=f"{failing}: {summary.split(';')[0].split(':')[0]}"[:80],
              sev=rng.choice(["sev2", "sev3"]), ts=ts, resolved_ts=ts + rng.randint(1, 4) * HOUR, summary=summary)
        w.link("Incident", iid, "AFFECTED", "Service", sid(failing), valid_from=ts)
        path = dependency_path(spec.deps, failing, culprit)
        assert path is not None, f"{failing} does not depend on {culprit}"
        truth_incidents.append(dict(
            incident=iid, family=fam.key, tier=fam.tier, pattern=fam.pattern, occurrence=occ + 1,
            failing_service=sid(failing), failing_test=failing_test, root_cause_service=sid(culprit),
            root_cause_commit=f"{iid}:culprit", hops=len(path) - 1, why_path=[sid(p) for p in path], ts=ts))
        # ticket + chat thread describing the symptom (never the cause)
        w.add("Ticket", id=f"tkt-{i + 1:02d}", title=summary.split(";")[0], status="closed", ts=ts + HOUR)
        w.link("Ticket", f"tkt-{i + 1:02d}", "ABOUT", "Incident", iid, valid_from=ts + HOUR)
        w.add("Thread", id=f"thr-inc-{i + 1:02d}", channel="#incidents", ts=ts + 600,
              text=f"{summary}. Rolling back is not obvious. Who has context on {failing}?")

    # --- background commits ---------------------------------------------------------
    for s in spec.services:
        for _ in range(spec.noise_commits_per_service):
            commits.append(dict(key=None, service=s, ts=rng.randint(start, END), special=False,
                                msg=rng.choice(NOISE_MSGS).format(s=s), author=person_for(s)))
    commits.sort(key=lambda c: (c["ts"], c["service"], c["msg"]))
    key_to_id = {}
    for k, c in enumerate(commits, 1):
        c["id"] = f"com-{k:03d}"
        if c["key"]:
            key_to_id[c["key"]] = c["id"]
        w.add("Commit", id=c["id"], sha=_sha(seed, k), ts=c["ts"], msg=c["msg"])
        w.link("Commit", c["id"], "AUTHORED_BY", "Person", c["author"])
        w.link("Commit", c["id"], "MODIFIED", "Service", sid(c["service"]))
    for t in truth_incidents:
        t["root_cause_commit"] = key_to_id[t["root_cause_commit"]]

    # --- PRs: ordinary commits pair up within a service, special ones get their own ---
    pr_n, open_pr = 0, {}
    for c in commits:
        pair = open_pr.get(c["service"])
        if not c["special"] and pair and rng.random() < 0.5:
            w.link("PR", pair, "CONTAINS", "Commit", c["id"])
            open_pr.pop(c["service"])
            continue
        pr_n += 1
        pid = f"pr-{pr_n:03d}"
        w.add("PR", id=pid, title=c["msg"], ts=c["ts"] + HOUR)
        w.link("PR", pid, "CONTAINS", "Commit", c["id"])
        if not c["special"]:
            open_pr[c["service"]] = pid

    # --- who knows what: authored commit counts per service ---------------------------
    counts = {}
    for c in commits:
        counts[(c["author"], c["service"])] = counts.get((c["author"], c["service"]), 0) + 1
    first_ts = {}
    for c in commits:
        first_ts.setdefault((c["author"], c["service"]), c["ts"])
    for (p, s), cnt in sorted(counts.items()):
        if cnt >= 3:
            w.link("Person", p, "KNOWS_ABOUT", "Service", sid(s), weight=cnt, valid_from=first_ts[(p, s)])

    # --- docs, decisions, supersession chains -------------------------------------------
    doc_n = 0
    for s in spec.services:
        doc_n += 1
        deps = ", ".join(b for a, b in spec.deps if a == s) or "no services"
        w.add("Doc", id=f"doc-{doc_n:03d}", title=f"{s} runbook", kind="runbook",
              body=f"Runbook for {s}, owned by team {owner_team[s]}. Calls {deps}. On alert check recent deploys and upstream health.")
        w.link("Doc", f"doc-{doc_n:03d}", "DESCRIBES", "Service", sid(s), valid_from=start)
    dec_id = {}
    for k, d in enumerate(spec.decisions, 1):
        dec_id[d["key"]] = f"dec-{k:02d}"
        dts = END - d["days_ago"] * DAY
        w.add("Decision", id=dec_id[d["key"]], title=d["title"], ts=dts, status=d["status"])
        doc_n += 1
        w.add("Doc", id=f"doc-{doc_n:03d}", title=f"ADR: {d['title']}", kind="adr", body=d["body"])
        w.link("Decision", dec_id[d["key"]], "DECIDED_IN", "Doc", f"doc-{doc_n:03d}", valid_from=dts)
        for s in d["concerns"]:
            w.link("Decision", dec_id[d["key"]], "CONCERNS", "Service", sid(s), valid_from=dts)
            w.link("Doc", f"doc-{doc_n:03d}", "DESCRIBES", "Service", sid(s), valid_from=dts)
        if d["supersedes"]:
            w.link("Decision", dec_id[d["key"]], "SUPERSEDES", "Decision", dec_id[d["supersedes"]], valid_from=dts)
    for k in range(10):  # general chatter
        s = rng.choice(list(spec.services))
        w.add("Thread", id=f"thr-gen-{k + 1:02d}", channel=f"#{owner_team[s]}", ts=rng.randint(start, END),
              text=rng.choice(["Anyone reviewed the latest change to {s}?", "Heads up: deploying {s} after lunch.",
                               "Why do we retry in {s} the way we do?", "Is the {s} runbook still accurate?"]).format(s=s))

    # --- ground truth (kept out of the graph) -----------------------------------------------
    w.truth = dict(tenant=spec.tenant, company=spec.company, seed=seed, incidents=truth_incidents)
    return w


def to_json(w: World) -> dict:
    return dict(tenant=w.spec.tenant, company=w.spec.company, seed=w.seed, nodes=w.nodes, edges=w.edges)


def write(w: World, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{w.spec.tenant}.json").write_text(json.dumps(to_json(w), indent=1, sort_keys=True))
    gt = "ground_truth.json" if w.spec.tenant == "alpha" else f"ground_truth_{w.spec.tenant}.json"
    (out / gt).write_text(json.dumps(w.truth, indent=1, sort_keys=True))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    for spec in (ALPHA, BETA):
        w = generate(spec, args.seed)
        write(w, Path(args.out))
        print(f"{spec.tenant}: {sum(len(v) for v in w.nodes.values())} nodes, {len(w.edges)} edges, "
              f"{len(w.truth['incidents'])} incidents")
