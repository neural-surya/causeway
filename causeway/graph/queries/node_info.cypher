// node_info: display label and name for a node id (used to draw why-paths in the UI).
MATCH (n {id: $id})
RETURN n.id AS id, labels(n)[0] AS label, coalesce(n.name, n.title, n.msg, n.id) AS name
