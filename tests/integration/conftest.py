"""真实外部服务的集成测试：服务不可达时自动跳过。

本机起好 docker compose（Qdrant/Neo4j/Postgres）后运行：
    uv run pytest tests/integration -q
"""
import socket

import pytest


def _reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def require(host_port):
    host, port = host_port
    if not _reachable(host, port):
        pytest.skip(f"{host}:{port} 不可达，跳过集成测试")
