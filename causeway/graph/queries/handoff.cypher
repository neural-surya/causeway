// handoff: pass an open task to another agent with a payload (JSON string of what was learned).
// Only an 'open' task can be handed off. Task -HANDED_OFF_VIA-> Handoff -TO-> Agent.
MATCH (t:Task {id: $task}) WHERE t.status = 'open'
SET t.status = 'handed_off'
MERGE (to:Agent {id: $to}) SET to.role = $to_role
CREATE (h:Handoff {id: $handoff, ts: $ts, payload: $payload})
CREATE (t)-[:HANDED_OFF_VIA]->(h)
CREATE (h)-[:TO]->(to)
RETURN h.id AS handoff
