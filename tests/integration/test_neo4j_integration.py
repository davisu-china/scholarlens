"""Neo4j 引用图真实读写（需 docker compose 起 Neo4j）。"""
import pytest
import pytest_asyncio

from core.adapters.neo4j_graph import Neo4jGraphStore

pytestmark = pytest.mark.parametrize("host_port", [("localhost", 7687)])


@pytest_asyncio.fixture
async def graph(require):
    g = Neo4jGraphStore()
    yield g
    import contextlib
    with contextlib.suppress(Exception):
        async with g._ensure().session() as s:
            await s.run("MATCH (p:Paper) WHERE p.id STARTS WITH 'it_' DETACH DELETE p")
    await g.close()


async def test_citation_expand(graph):
    for a, b in [("it_a", "it_b"), ("it_b", "it_c")]:
        await graph.add_citation(a, b)
    assert await graph.expand(["it_a"], hops=1) == ["it_b"]
    assert set(await graph.expand(["it_a"], hops=2)) == {"it_b", "it_c"}
