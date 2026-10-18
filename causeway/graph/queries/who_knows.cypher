// who_knows: who to ask about a service.
// owners  = members of the team that OWNS the service (role 'owner')
// experts = people with KNOWS_ABOUT edges, weight = commits they authored there (role 'expert')
// Only currently valid facts count (valid_to IS NULL). path_ids is the evidence chain.
MATCH (t:Team)-[o:OWNS]->(s:Service {id: $service})
WHERE o.valid_to IS NULL
MATCH (p:Person)-[:MEMBER_OF]->(t)
RETURN p.id AS person, p.name AS name, 'owner' AS role, 0 AS weight, [p.id, t.id, s.id] AS path_ids
UNION
MATCH (p:Person)-[k:KNOWS_ABOUT]->(s:Service {id: $service})
WHERE k.valid_to IS NULL
RETURN p.id AS person, p.name AS name, 'expert' AS role, k.weight AS weight, [p.id, s.id] AS path_ids
