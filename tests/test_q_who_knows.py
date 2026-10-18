from collections import Counter

from causeway.graph.queries import run


def test_owners_are_the_owning_team_members(graph, world):
    team_of = {e["dst"][1]: e["src"][1] for e in world.edges if e["rel"] == "OWNS"}
    members = {}
    for e in world.edges:
        if e["rel"] == "MEMBER_OF":
            members.setdefault(e["dst"][1], set()).add(e["src"][1])
    for svc, team in team_of.items():
        owners = {r["person"] for r in run(graph, "who_knows", service=svc) if r["role"] == "owner"}
        assert owners == members[team]


def test_expert_weights_equal_authored_commit_counts(graph, world):
    author = {e["src"][1]: e["dst"][1] for e in world.edges if e["rel"] == "AUTHORED_BY"}
    svc_of = {e["src"][1]: e["dst"][1] for e in world.edges if e["rel"] == "MODIFIED"}
    counts = Counter((author[c], svc_of[c]) for c in author)
    for svc in ("svc-payments", "svc-user-profile"):
        got = {r["person"]: r["weight"] for r in run(graph, "who_knows", service=svc) if r["role"] == "expert"}
        want = {p: n for (p, s), n in counts.items() if s == svc and n >= 3}
        assert got == want and got


def test_culprit_author_is_findable_as_expert_or_owner(graph, world, truth):
    author = {e["src"][1]: e["dst"][1] for e in world.edges if e["rel"] == "AUTHORED_BY"}
    for t in truth.values():
        people = {r["person"] for r in run(graph, "who_knows", service=t["root_cause_service"])}
        assert author[t["root_cause_commit"]] in people


def test_paths_start_at_the_person_and_end_at_the_service(graph):
    for r in run(graph, "who_knows", service="svc-ledger"):
        assert r["path_ids"][0] == r["person"] and r["path_ids"][-1] == "svc-ledger"
