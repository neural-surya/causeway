import pytest

from causeway.data.generate import generate
from causeway.data.loader import load_world
from causeway.data.specs import ALPHA
from causeway.graph.client import get_db


@pytest.fixture(scope="session")
def world():
    return generate(ALPHA, 42)


@pytest.fixture(scope="session")
def graph(world):
    """Seeded alpha world in a scratch graph (never touches tenant_alpha)."""
    g = get_db().select_graph("queries_test_alpha")
    load_world(g, world)
    yield g
    g.delete()


@pytest.fixture(scope="session")
def truth(world):
    return {t["incident"]: t for t in world.truth["incidents"]}
