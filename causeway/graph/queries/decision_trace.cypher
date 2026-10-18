// decision_trace: why is a service built the way it is?
// Every decision that CONCERNS the service, the document it was decided in, and which newer decision
// (if any) SUPERSEDES it. A decision with superseded_by = null is the current one.
MATCH (d:Decision)-[:CONCERNS]->(s:Service {id: $service})
OPTIONAL MATCH (d)-[:DECIDED_IN]->(doc:Doc)
OPTIONAL MATCH (n:Decision)-[:SUPERSEDES]->(d)
RETURN d.id AS decision, d.title AS title, d.status AS status, d.ts AS ts, doc.id AS doc,
       n.id AS superseded_by,
       [x IN [d.id, doc.id, s.id] WHERE x IS NOT NULL] AS path_ids
ORDER BY d.ts
