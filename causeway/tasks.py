"""Agent coordination through the graph: Task and Handoff nodes."""
import json

from causeway.graph.queries import write


def open_task(graph, task, episode, incident, agent, role, kind, ts):
    return write(graph, "open_task", task=task, episode=episode, incident=incident, agent=agent,
                 role=role, kind=kind, ts=ts)


def handoff(graph, task, handoff_id, to, to_role, payload: dict, ts):
    return write(graph, "handoff", task=task, handoff=handoff_id, to=to, to_role=to_role,
                 payload=json.dumps(payload, sort_keys=True), ts=ts)


def claim_task(graph, task, agent) -> dict | None:
    """Returns the handoff payload if this agent won the claim, else None."""
    rows = write(graph, "claim_task", task=task, agent=agent)
    return json.loads(rows[0]["payload"]) if rows else None
