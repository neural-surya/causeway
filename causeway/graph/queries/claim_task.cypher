// claim_task: atomic claim. The status test and the status change happen in ONE write query, and
// FalkorDB executes writes to a graph one at a time, so two agents cannot both claim the same task:
// the loser's WHERE no longer matches and it gets zero rows. Returns the handoff payload to the winner.
MATCH (t:Task {id: $task})-[:HANDED_OFF_VIA]->(h:Handoff)-[:TO]->(a:Agent {id: $agent})
WHERE t.status = 'handed_off'
SET t.status = 'claimed'
CREATE (a)-[:CLAIMED]->(t)
RETURN t.id AS task, h.payload AS payload
