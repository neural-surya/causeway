from causeway.embed import embed
from causeway.graph.queries import run


def entry(graph, text, k=6):
    return run(graph, "entry_points", q=embed(text), k=k)


def test_alert_text_surfaces_failing_service_in_top3(graph, truth):
    hits = 0
    for t in truth.values():
        [ctx] = run(graph, "incident_context", incident=t["incident"])
        services = []
        for r in entry(graph, ctx["summary"]):
            if r["service"] not in services:
                services.append(r["service"])
        hits += t["failing_service"] in services[:3]
    assert hits >= 11, hits  # lexical stand-in embedding; real model should do at least as well


def test_service_name_query_returns_its_runbook_first(graph):
    assert entry(graph, "ledger runbook")[0]["title"] == "ledger runbook"


def test_failing_test_maps_to_failing_service(graph, truth):
    for t in truth.values():
        rows = run(graph, "service_for_test", test=t["failing_test"])
        assert [r["service"] for r in rows] == [t["failing_service"]]


def test_unknown_test_returns_nothing(graph):
    assert run(graph, "service_for_test", test="test_nope") == []
