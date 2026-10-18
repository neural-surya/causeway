// similar_incidents: earlier incidents whose dependency neighbourhood overlaps this one's.
// Neighbourhood = the affected service plus everything it depends on within 2 hops.
// Score = Jaccard(neighbourhood_a, neighbourhood_b). Only incidents BEFORE this one count.
// Uses AFFECTED edges only: root causes are not in the graph until memory writes them.
MATCH (i:Incident {id: $incident})-[:AFFECTED]->(s:Service)
OPTIONAL MATCH (s)-[:DEPENDS_ON*1..2]->(d:Service)
WITH i, collect(DISTINCT s.id) + collect(DISTINCT d.id) AS a
MATCH (j:Incident)-[:AFFECTED]->(t:Service)
WHERE j.ts < i.ts
OPTIONAL MATCH (t)-[:DEPENDS_ON*1..2]->(e:Service)
WITH i, a, j, t, collect(DISTINCT t.id) + collect(DISTINCT e.id) AS b
WITH i, j, t, a, b, [x IN a WHERE x IN b] AS shared
RETURN j.id AS similar, t.id AS service, j.ts AS ts, shared,
       size(shared) * 1.0 / (size(a) + size(b) - size(shared)) AS jaccard
ORDER BY jaccard DESC, ts DESC
