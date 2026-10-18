// supersede_belief: replace a current belief without deleting history.
// Closes the old belief (valid_to = $ts), creates the new one, links new -SUPERSEDES-> old with a reason,
// and copies ABOUT / SUPPORTED_BY links so `recall` finds the new belief. Does nothing if the old belief
// is already closed.
MATCH (old:Belief {id: $old}) WHERE old.valid_to IS NULL
SET old.valid_to = $ts
CREATE (new:Belief {id: $new, text: $text, confidence: $confidence, valid_from: $ts, embedding: vecf32($emb)})
CREATE (new)-[:SUPERSEDES {reason: $reason}]->(old)
WITH old, new
MATCH (old)-[:ABOUT]->(x)
CREATE (new)-[:ABOUT]->(x)
WITH DISTINCT old, new
MATCH (old)-[:SUPPORTED_BY]->(e)
CREATE (new)-[:SUPPORTED_BY]->(e)
RETURN new.id AS belief
