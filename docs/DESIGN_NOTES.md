# Design notes

## 1.1 FalkorDB + client
- One FalkorDB instance, one graph per tenant (`tenant_<id>`), so isolation is structural.
- Reads use `ro_query`, writes `query`; all values go through `params`, never string formatting.
