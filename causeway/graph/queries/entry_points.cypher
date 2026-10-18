// entry_points: map free text (alert, log line) to services, via vector search over Docs.
// $q is the embedded text. Vector search is only the front door: it finds runbooks/ADRs whose
// DESCRIBES edge leads to a Service; all reasoning after that is graph traversal.
// score is cosine DISTANCE (lower = closer).
CALL db.idx.vector.queryNodes('Doc', 'embedding', $k, vecf32($q)) YIELD node, score
MATCH (node)-[:DESCRIBES]->(s:Service)
RETURN s.id AS service, node.id AS doc, node.title AS title, score,
       [node.id, s.id] AS path_ids
ORDER BY score
