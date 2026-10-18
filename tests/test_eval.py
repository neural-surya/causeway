from eval.run_eval import evaluate, rate


def test_graph_beats_flat_rag_and_memory_helps():
    r = evaluate()
    assert all(len(rows) == 12 for rows in r.values())
    assert rate(r["graph"], "top3") > rate(r["flat_rag"], "top3")
    assert rate(r["graph+mem"], "top1") > rate(r["graph"], "top1")
    assert all(row["claim_verified"] for row in r["graph"] + r["graph+mem"])
    # first occurrence of each family is identical with and without memory (nothing to recall yet)
    first = lambda rows: [x["top1"] for x in rows if x["occurrence"] == 1]
    assert first(r["graph"]) == first(r["graph+mem"])
