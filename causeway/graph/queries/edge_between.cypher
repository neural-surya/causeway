// edge_between: does any relationship connect two nodes (either direction)? Used by the path verifier.
// Returns one row per connecting relationship with its type and direction.
MATCH (a {id: $a})-[r]-(b {id: $b})
RETURN type(r) AS rel, startNode(r).id = $a AS forward
