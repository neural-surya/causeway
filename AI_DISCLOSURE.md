# AI Disclosure

This project was built with **Claude Code (Claude Sonnet 5.5)** as a coding assistant, directed by the human author
(Suryakanta Mohapatra) across the hackathon window.

## What Claude Code generated
Essentially all code and docs in the repo, at the author's direction: the Docker/Make scaffold; graph client,
schema and indexes; the synthetic-world generator and loader; every `.cypher` query; the path verifier; the
suspect ranker; memory (episodes, beliefs, supersession); Task/Handoff coordination; the two deterministic agents;
the MCP server; the FastAPI app and static page; the eval harness; all tests; README and docs.
The vendored `causeway/static/cytoscape.min.js` is the unmodified Cytoscape.js 3.30.2 release.

## What the human did
Set the product concept, the compressed scope and the working rules; reviewed an explanation of each task before
continuing; made the design decisions that were put to them (embedding stand-in, family design, cuts); chose
the repo, hackathon tracks and submission. Verification of FalkorDB syntax was done by Claude Code against
docs.falkordb.com and by probing the live database.

## What is NOT AI-generated at runtime
The product makes no LLM calls: the agents are deterministic code. All data is synthetic, produced by a seeded
generator; no real company, personal or private data is used.

## Known honesty notes
See "Honest limitations" in the README (synthetic data favours memory, small sample, stand-in embeddings).
