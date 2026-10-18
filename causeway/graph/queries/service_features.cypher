// service_features: per-service signals used when ranking suspect commits.
//   dependents  = how many distinct services transitively call this one (blast radius / centrality proxy)
//   max_flaky   = highest flaky_score among tests covering it (a noisy service explains false alarms)
//   tests       = number of covering tests
// One row per service, for all services in the tenant graph.
MATCH (s:Service)
OPTIONAL MATCH (c:Service)-[:DEPENDS_ON*1..4]->(s)
WITH s, count(DISTINCT c) AS dependents
OPTIONAL MATCH (t:Test)-[:COVERS]->(s)
RETURN s.id AS service, dependents, coalesce(max(t.flaky_score), 0.0) AS max_flaky, count(t) AS tests
ORDER BY service
