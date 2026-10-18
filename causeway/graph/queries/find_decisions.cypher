// find_decisions: every decision with the services it concerns, its document text, and the newer
// decision (if any) that SUPERSEDES it. Lets Q&A match a question to a decision by its words and then
// walk the supersession chain. One row per decision.
MATCH (d:Decision)
OPTIONAL MATCH (d)-[:CONCERNS]->(s:Service)
WITH d, collect(s.id) AS services
OPTIONAL MATCH (d)-[:DECIDED_IN]->(doc:Doc)
OPTIONAL MATCH (n:Decision)-[:SUPERSEDES]->(d)
RETURN d.id AS decision, d.title AS title, d.status AS status, d.ts AS ts, services,
       doc.id AS doc, doc.body AS body, n.id AS superseded_by
ORDER BY d.ts
