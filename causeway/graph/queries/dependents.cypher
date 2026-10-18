// dependents: the reverse view. Which services call this one, up to $depth hops (who is hurt if it breaks).
// Same path semantics as trace_dependencies. path_ids runs from the caller down to $service.
MATCH p = (c:Service)-[:DEPENDS_ON*1..4]->(s:Service {id: $service})
WHERE length(p) <= $depth
RETURN c.id AS dependent, length(p) AS hops, [n IN nodes(p) | n.id] AS path_ids
ORDER BY hops, dependent
