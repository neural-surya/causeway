// list_incidents: incidents for the picker, oldest first, with whether memory already holds a conclusion.
MATCH (i:Incident)-[:AFFECTED]->(s:Service)
OPTIONAL MATCH (e:Episode)-[:INVESTIGATED]->(i) WHERE e.outcome = 'resolved'
RETURN i.id AS id, i.title AS title, i.ts AS ts, s.id AS service, count(e) > 0 AS remembered
ORDER BY i.ts
