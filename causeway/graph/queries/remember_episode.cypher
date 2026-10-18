// remember_episode: record a finished investigation. Idempotent (MERGE on ids): re-running the same
// episode creates no duplicates, so concurrent/retried writes cannot double-count.
// Writes: Episode -INVESTIGATED-> Incident, Episode -CONCLUDED-> Belief, Belief -ABOUT-> Commit and Service,
// Belief -SUPPORTED_BY-> Episode, and Incident -CAUSED_BY-> Commit (the resolved root cause becomes a fact).
MATCH (i:Incident {id: $incident}), (c:Commit {id: $commit})-[:MODIFIED]->(s:Service)
MERGE (e:Episode {id: $episode})
SET e.ts = $ts, e.summary = $summary, e.outcome = 'resolved'
MERGE (b:Belief {id: $belief})
SET b.text = $text, b.confidence = $confidence, b.valid_from = $ts, b.embedding = vecf32($emb)
MERGE (e)-[:INVESTIGATED]->(i)
MERGE (e)-[:CONCLUDED]->(b)
MERGE (b)-[:ABOUT]->(c)
MERGE (b)-[:ABOUT]->(s)
MERGE (b)-[:SUPPORTED_BY]->(e)
MERGE (i)-[:CAUSED_BY]->(c)
RETURN e.id AS episode, b.id AS belief
