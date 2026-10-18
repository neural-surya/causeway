// recall: what do we already believe about past root causes? Returns beliefs with the culprit commit
// they point at. By default only CURRENT beliefs (valid_to IS NULL); $include_history also returns
// superseded ones. Only episodes finished before $as_of count (no peeking at the future).
MATCH (b:Belief)-[:ABOUT]->(c:Commit)-[:MODIFIED]->(s:Service)
WHERE ($include_history OR b.valid_to IS NULL)
MATCH (b)-[:SUPPORTED_BY]->(e:Episode)-[:INVESTIGATED]->(i:Incident)
WHERE e.ts <= $as_of
RETURN b.id AS belief, b.text AS text, b.confidence AS confidence, b.valid_from AS valid_from,
       b.valid_to AS valid_to, c.id AS commit, c.msg AS commit_msg, s.id AS service, i.id AS incident,
       [b.id, c.id, s.id] AS path_ids
ORDER BY b.valid_from DESC
