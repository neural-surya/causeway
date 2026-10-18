// open_task: the triage agent opens a unit of work for an investigation.
// Creates Task(status 'open') -PART_OF-> Episode (the episode node is created here if absent, filled in
// by remember_episode later) and registers the opening agent.
MERGE (e:Episode {id: $episode})
MERGE (a:Agent {id: $agent}) SET a.role = $role
CREATE (t:Task {id: $task, kind: $kind, status: 'open', incident: $incident, ts: $ts})
CREATE (t)-[:PART_OF]->(e)
RETURN t.id AS task
