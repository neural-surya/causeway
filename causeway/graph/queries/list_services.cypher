// list_services: all services (id, name, tier). Used to find which service a question is about.
MATCH (s:Service) RETURN s.id AS id, s.name AS name, s.tier AS tier ORDER BY s.name
