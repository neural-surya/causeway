// service_for_test: the service(s) a failing test covers. Exact match on the test name or id.
MATCH (t:Test)-[:COVERS]->(s:Service)
WHERE t.id = $test OR t.name = $test
RETURN t.id AS test, t.name AS test_name, t.flaky_score AS flaky_score, s.id AS service,
       [t.id, s.id] AS path_ids
