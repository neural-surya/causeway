"""Company-brain Q&A: answer a plain-English question from the graph, with cited, verified paths.

Deterministic (no LLM): a question is routed to an intent by keywords, the answer is built from the same
graph queries the agents use, and every claim's path goes through the verifier. A question that matches
no intent is answered with "I can't answer that" and no claims; nothing is guessed.
"""
import re

from causeway.graph.queries import run
from causeway.investigate import graph_elements

STOP = set("""a an the of in on at to for is are was were be do does did we our us i you why how what which who
whom whose when where it its this that these those and or but not no way thing things chose choose chosen decide
decided decision use used using have has had should would could can about by with from as so than then there
here out up down over under again""".split())


def _stem(w):
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    return w[:-1] if w.endswith("s") and len(w) > 3 else w


def _tokens(text):
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def find_service(session, q):
    """First service named in the question ('api-gateway' or 'api gateway'), as (id, name) or None."""
    low, best = q.lower(), None
    for s in run(session.graph, "list_services"):
        for form in {s["name"], s["name"].replace("-", " ")}:
            pos = low.find(form)
            if pos >= 0 and (best is None or pos < best[0]):
                best = (pos, s["id"], s["name"])
    return (best[1], best[2]) if best else None


def intent_of(q):
    low = q.lower()
    if re.search(r"\bwho owns\b|\bowner\b|\bowned by\b|\bowns\b", low):
        return "owners"
    if re.search(r"who knows|ask about|expert|who should", low):
        return "experts"
    if re.search(r"\bwhy\b|decision|decided|\bchose\b|\bchoose\b", low):
        return "decisions"
    if re.search(r"\bdepend|dependenc|\bcalls?\b", low):
        return "dependencies" if re.search(r"\bdoes\b|\bdo\b|dependencies", low) else "dependents"
    if re.search(r"\btests?\b", low):
        return "tests"
    return None


def _claim(text, path, entities=None):
    return dict(text=text, path_ids=path, entities=entities or [path[0], path[-1]])


def ask(session, question: str) -> dict:
    g, intent = session.graph, intent_of(question)
    svc = find_service(session, question)
    claims, answer = [], None

    if intent in ("owners", "experts", "dependencies", "dependents", "tests") and not svc:
        return _finish(session, question, intent, "Which service do you mean? I could not find one in the question.", [])

    if intent == "owners":
        rows = [r for r in session.who_knows(svc[0]) if r["role"] == "owner"]
        team = rows[0]["path_ids"][1].removeprefix("team-") if rows else "?"
        answer = f"{svc[1]} is owned by team {team}: " + ", ".join(r["name"] for r in rows) + "."
        claims = [_claim(f"{r['name']} is on the team that owns {svc[1]}", r["path_ids"]) for r in rows]

    elif intent == "experts":
        rows = sorted((r for r in session.who_knows(svc[0]) if r["role"] == "expert"), key=lambda r: -r["weight"])[:3]
        answer = (f"Ask about {svc[1]}: " + ", ".join(f"{r['name']} ({r['weight']} commits)" for r in rows) + "."
                  if rows else f"Nobody has authored enough commits on {svc[1]} to count as an expert.")
        claims = [_claim(f"{r['name']} has authored {r['weight']} commits on {svc[1]}", r["path_ids"]) for r in rows]

    elif intent in ("dependencies", "dependents"):
        if intent == "dependencies":
            rows = [r for r in session.trace_dependencies(svc[0], 1)]
            names = [r["dependency"] for r in rows]
            answer = f"{svc[1]} directly depends on: " + ", ".join(n.removeprefix("svc-") for n in names) + "."
            claims = [_claim(f"{svc[1]} depends on {r['dependency'].removeprefix('svc-')}", r["path_ids"]) for r in rows]
        else:
            rows = [r for r in run(g, "dependents", service=svc[0], depth=1)]
            names = [r["dependent"] for r in rows]
            answer = f"Services that directly depend on {svc[1]}: " + ", ".join(n.removeprefix("svc-") for n in names) + "."
            claims = [_claim(f"{r['dependent'].removeprefix('svc-')} depends on {svc[1]}", r["path_ids"]) for r in rows]
        if not rows:
            answer = f"No direct {'dependencies' if intent == 'dependencies' else 'dependents'} found for {svc[1]}."

    elif intent == "tests":
        rows = run(g, "tests_for_service", service=svc[0])
        answer = f"{svc[1]} is covered by: " + ", ".join(f"{r['name']} (flaky {r['flaky_score']})" for r in rows) + "."
        claims = [_claim(f"{r['name']} covers {svc[1]}", r["path_ids"]) for r in rows]

    elif intent == "decisions":
        answer, claims = _decisions(session, question, svc)

    if answer is None:
        return _finish(session, question, None, "I can't answer that. I can answer who owns or knows a service, "
                       "what it depends on or what depends on it, which tests cover it, and why a design decision was made.", [])
    return _finish(session, question, intent, answer, claims)


def _decisions(session, question, svc):
    rows = run(session.graph, "find_decisions")
    by_id = {r["decision"]: r for r in rows}
    pred = {r["superseded_by"]: r["decision"] for r in rows if r["superseded_by"]}
    skip = _tokens(svc[1].replace("-", " ")) if svc else set()
    want = _tokens(question) - skip
    pool = [r for r in rows if not svc or svc[0] in r["services"]]
    scored = sorted(((len(want & _tokens(r["title"] + " " + (r["body"] or ""))), r) for r in pool), key=lambda x: (-x[0], -x[1]["ts"]))  # best match; ties go to the newest decision
    if not scored or scored[0][0] == 0:
        return None, []
    top = scored[0][1]["decision"]
    chain = [top]
    while chain[0] in pred:      # walk back to the oldest
        chain.insert(0, pred[chain[0]])
    while by_id[chain[-1]]["superseded_by"]:        # walk forward to the current one
        chain.append(by_id[chain[-1]]["superseded_by"])
    cur = by_id[chain[-1]]
    answer = f"Currently: {cur['title']}."
    if len(chain) > 1:
        answer += " History (oldest first): " + " -> ".join(by_id[d]["title"] for d in chain) + "."
    if by_id[top]["superseded_by"]:
        answer = f"'{by_id[top]['title']}' has since been superseded. " + answer
    claims = []
    for d in chain:
        r = by_id[d]
        claims.append(_claim(f"'{r['title']}' was decided in {r['doc']}", [d, r["doc"]]))
    for newer, older in zip(chain[1:], chain):
        claims.append(_claim(f"'{by_id[newer]['title']}' supersedes '{by_id[older]['title']}'", [newer, older]))
    return answer, claims


def _finish(session, question, intent, answer, claims):
    for c in claims:
        v = session.verify(c)
        c["verified"], c["reason"] = v.ok, v.reason
    return dict(question=question, intent=intent, answer=answer, claims=claims,
                elements=graph_elements(session.graph, [c["path_ids"] for c in claims]))
