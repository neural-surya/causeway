// trace_dependencies: what a service depends on, up to $depth hops (the blast-radius view for a failure).
// One row per path. `path_ids` alternates service ids along the path and is the evidence for a claim
// like "payments depends on fraud".
// NOTE: variable-length patterns return every path, not only the shortest, so callers take min(hops)
// per target. Uses *1..N (a fixed *N returns nothing on this FalkorDB build).
MATCH p = (s:Service {id: $service})-[:DEPENDS_ON*1..4]->(d:Service)
WHERE length(p) <= $depth
RETURN d.id AS dependency, length(p) AS hops, [n IN nodes(p) | n.id] AS path_ids
ORDER BY hops, dependency
