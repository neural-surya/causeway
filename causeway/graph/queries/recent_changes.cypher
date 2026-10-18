// recent_changes: commits that touched a service or anything it depends on, in the window before $as_of.
// This is the candidate pool for root-cause analysis. `$as_of` (the incident time) is mandatory so an
// investigation can never see changes made after the failure. `hops` is the dependency distance from
// the failing service to the changed service (0 = the service itself); path_ids is the evidence path:
// failing service ... changed service, then the commit, then its author.
MATCH p = (s:Service {id: $service})-[:DEPENDS_ON*0..4]->(d:Service)<-[:MODIFIED]-(c:Commit)
WHERE length(p) - 1 <= $depth
  AND c.ts <= $as_of AND c.ts > $as_of - $window_hours * 3600
WITH c, d, p ORDER BY length(p)
WITH c, d, head(collect(p)) AS p   // a commit reachable by several paths is reported once, via the shortest
MATCH (c)-[:AUTHORED_BY]->(a:Person)
RETURN c.id AS commit, c.sha AS sha, c.msg AS msg, c.ts AS ts,
       d.id AS service, length(p) - 1 AS hops, a.id AS author,
       [n IN nodes(p) | n.id] + [a.id] AS path_ids
ORDER BY c.ts DESC, hops
