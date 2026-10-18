// commit_message: the message of one commit by id.
MATCH (c:Commit {id: $commit}) RETURN c.msg AS msg
