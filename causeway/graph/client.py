"""FalkorDB connection helpers. One graph per tenant: tenant_<id>."""
import os

from falkordb import FalkorDB, Graph


def get_db() -> FalkorDB:
    return FalkorDB(
        host=os.environ.get("FALKORDB_HOST", "localhost"),
        port=int(os.environ.get("FALKORDB_PORT", "6379")),
        password=os.environ.get("FALKORDB_PASSWORD") or None,
    )


def tenant_graph(tenant: str, db: FalkorDB | None = None) -> Graph:
    return (db or get_db()).select_graph(f"tenant_{tenant}")
