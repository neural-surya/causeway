// incident_context: the starting facts of an investigation.
// Given an incident id, return its alert text, time, and the service that showed the symptom.
// Used by every tool that needs "as of when" (ts) and "where" (service_id).
MATCH (i:Incident {id: $incident})-[:AFFECTED]->(s:Service)
RETURN i.id AS incident, i.summary AS summary, i.ts AS ts,
       s.id AS service_id, s.name AS service_name
