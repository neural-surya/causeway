// all_commits_window: every commit in the window before $as_of, with no graph structure used.
// Corpus for the flat-RAG baseline (text similarity only); deliberately ignores dependencies.
MATCH (c:Commit)-[:MODIFIED]->(s:Service)
WHERE c.ts <= $as_of AND c.ts > $as_of - $window_hours * 3600
RETURN c.id AS commit, c.msg AS msg, c.ts AS ts, s.id AS service
