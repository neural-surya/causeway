"""Task 2.4: ten scripted company-brain questions. Answers are checked against the generated world and
every claim's path must verify against the graph."""
import pytest

from causeway.qa import ask, find_service, intent_of
from causeway.session import Session


@pytest.fixture
def s(graph):
    return Session("alpha", graph)


def team_members(world, service):
    team = next(e["src"][1] for e in world.edges if e["rel"] == "OWNS" and e["dst"][1] == service)
    ids = {e["src"][1] for e in world.edges if e["rel"] == "MEMBER_OF" and e["dst"][1] == team}
    return {p["name"] for p in world.nodes["Person"] if p["id"] in ids}


def check(r, intent):
    assert r["intent"] == intent, r
    assert r["claims"] and all(c["verified"] for c in r["claims"]), [c for c in r["claims"] if not c["verified"]]
    return r["answer"]


def test_q01_who_owns_payments(s, world):
    a = check(ask(s, "Who owns payments?"), "owners")
    assert all(n in a for n in team_members(world, "svc-payments"))


def test_q02_who_owns_ledger_service(s, world):
    a = check(ask(s, "Who owns the ledger service?"), "owners")
    assert all(n in a for n in team_members(world, "svc-ledger"))


def test_q03_who_knows_user_profile(s, world):
    r = ask(s, "Who knows about user-profile?")
    a = check(r, "experts")
    top = max((e for e in world.edges if e["rel"] == "KNOWS_ABOUT" and e["dst"][1] == "svc-user-profile"),
              key=lambda e: e["props"]["weight"])
    name = next(p["name"] for p in world.nodes["Person"] if p["id"] == top["src"][1])
    assert name in a


def test_q04_who_should_i_ask_about_fraud(s):
    check(ask(s, "Who should I ask about fraud?"), "experts")


def test_q05_what_does_api_gateway_depend_on(s):
    a = check(ask(s, "What does the api-gateway depend on?"), "dependencies")
    for dep in ("auth", "orders", "payments", "user-profile"):
        assert dep in a


def test_q06_what_depends_on_ledger(s):
    a = check(ask(s, "What depends on ledger?"), "dependents")
    assert "payments" in a and "billing" in a and "api-gateway" not in a  # direct dependents only


def test_q07_why_do_we_retry_in_payments(s):
    r = ask(s, "Why do we retry the way we do in payments?")
    a = check(r, "decisions")
    assert a.startswith("Currently: Retry budget of 10 percent extra load, never retry 4xx.")  # asked about now
    assert "Retry failed gateway calls 3 times immediately" in a and "exponential backoff" in a  # the history
    assert any("supersedes" in c["text"] for c in r["claims"])


def test_q08_why_exponential_backoff_reports_it_was_superseded(s):
    a = check(ask(s, "Why did we choose exponential backoff with jitter?"), "decisions")
    assert "has since been superseded" in a and "Retry budget" in a


def test_q09_why_schema_migrations(s):
    a = check(ask(s, "Why are schema migrations expand then contract?"), "decisions")
    assert "expand then contract" in a.lower()


def test_q10_which_tests_cover_orders(s, world):
    a = check(ask(s, "Which tests cover orders?"), "tests")
    covers = {e["src"][1] for e in world.edges if e["rel"] == "COVERS" and e["dst"][1] == "svc-orders"}
    names = [t["name"] for t in world.nodes["Test"] if t["id"] in covers]
    assert len(names) == 3 and all(n in a for n in names)


def test_unanswerable_question_gets_no_claims(s):
    r = ask(s, "What is the weather in Paris?")
    assert r["intent"] is None and r["claims"] == [] and "can't answer" in r["answer"]


def test_service_questions_without_a_service_ask_which(s):
    r = ask(s, "Who owns it?")
    assert r["claims"] == [] and "Which service" in r["answer"]


def test_service_and_intent_detection():
    assert intent_of("What does X depend on") == "dependencies" and intent_of("What depends on X") == "dependents"
