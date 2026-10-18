"""Task 1.3 (generator): deterministic, right shape, ground truth consistent with the world."""
import pytest

from causeway.data.generate import dependency_path, generate
from causeway.data.specs import ALPHA, BETA


@pytest.fixture(scope="module")
def alpha():
    return generate(ALPHA, 42)


def test_deterministic_and_seed_sensitive(alpha):
    again = generate(ALPHA, 42)
    assert (alpha.nodes, alpha.edges, alpha.truth) == (again.nodes, again.edges, again.truth)
    assert generate(ALPHA, 43).nodes != alpha.nodes


def test_counts_match_spec(alpha):
    assert len(alpha.nodes["Service"]) == 10
    assert len(alpha.nodes["Incident"]) == 12
    assert 250 <= len(alpha.nodes["Commit"]) <= 400
    fams = {}
    for t in alpha.truth["incidents"]:
        fams.setdefault(t["family"], []).append(t)
    assert len(fams) == 4 and all(len(v) == 3 for v in fams.values())
    assert len(BETA.services) < len(ALPHA.services)


def test_dependency_graph_is_acyclic(alpha):
    for a, b in ALPHA.deps:
        assert dependency_path(ALPHA.deps, b, a) is None


def test_ground_truth_matches_world(alpha):
    commits = {c["id"]: c for c in alpha.nodes["Commit"]}
    incidents = {i["id"]: i for i in alpha.nodes["Incident"]}
    modified = {e["src"][1]: e["dst"][1] for e in alpha.edges if e["rel"] == "MODIFIED"}
    for t in alpha.truth["incidents"]:
        c = commits[t["root_cause_commit"]]
        assert modified[c["id"]] == t["root_cause_service"]
        gap = incidents[t["incident"]]["ts"] - c["ts"]
        assert 0 < gap <= 48 * 3600
        names = [s.removeprefix("svc-") for s in t["why_path"]]
        assert len(names) - 1 == t["hops"]
        assert dependency_path(ALPHA.deps, names[0], names[-1]) == names
        assert t["hops"] == 0 if t["tier"] == "easy" else t["hops"] >= 2


def test_answers_are_not_in_the_graph(alpha):
    assert not any(e["rel"] == "CAUSED_BY" for e in alpha.edges)
    for i in alpha.nodes["Incident"]:
        assert not {"family", "tier", "root_cause_commit"} & set(i)


def test_supersession_chain_exists(alpha):
    sup = [e for e in alpha.edges if e["rel"] == "SUPERSEDES"]
    assert len(sup) >= 3
    old = {e["dst"][1] for e in sup}
    status = {d["id"]: d["status"] for d in alpha.nodes["Decision"]}
    assert all(status[o] == "superseded" for o in old)


def test_decoys_are_more_recent_than_culprit_for_hard(alpha):
    commits = {c["id"]: c for c in alpha.nodes["Commit"]}
    modified = {e["src"][1]: e["dst"][1] for e in alpha.edges if e["rel"] == "MODIFIED"}
    for t in alpha.truth["incidents"]:
        if t["tier"] != "hard":
            continue
        culprit_ts = commits[t["root_cause_commit"]]["ts"]
        newer = [c for c in commits.values() if modified[c["id"]] == t["failing_service"]
                 and culprit_ts < c["ts"] < next(i["ts"] for i in alpha.nodes["Incident"] if i["id"] == t["incident"])]
        assert len(newer) >= 2
