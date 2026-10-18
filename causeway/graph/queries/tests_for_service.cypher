// tests_for_service: tests that cover a service, with their flakiness. path_ids is the evidence.
MATCH (t:Test)-[:COVERS]->(s:Service {id: $service})
RETURN t.id AS test, t.name AS name, t.flaky_score AS flaky_score, [t.id, s.id] AS path_ids
ORDER BY t.name
