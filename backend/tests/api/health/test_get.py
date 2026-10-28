"""健康检查端点用例。

覆盖的 Scenario：
- PC-12 依赖全部可达 → 200 且 deps 三项 up
- PC-13 向量库不可达 → 503 且 deps.qdrant=down
- PC-04 的例外条款：/health 不走统一信封
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_live_returns_200_without_probing_deps(client: AsyncClient) -> None:
    """/health/live 不查依赖：即使三个依赖全挂也必须 200。"""
    response = await client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "deps" not in body


async def test_health_returns_200_and_all_deps_up(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PC-12：三个依赖可达时返回 200，deps 三项 up，且响应头带 request_id。"""

    async def _all_up() -> dict[str, str]:
        return {"db": "up", "qdrant": "up", "llm": "up"}

    monkeypatch.setattr("app.api.v1.health.collect_deps", _all_up)

    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["deps"] == {"db": "up", "qdrant": "up", "llm": "up"}
    assert body["version"]
    assert body["commit"]
    assert body["time"].endswith("Z")
    assert len(response.headers["X-Request-ID"]) == 26


async def test_health_returns_503_when_qdrant_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PC-13：qdrant 不可达 → 503 且 deps.qdrant=down，其余两项仍报 up。"""

    async def _qdrant_down() -> dict[str, str]:
        return {"db": "up", "qdrant": "down", "llm": "up"}

    monkeypatch.setattr("app.api.v1.health.collect_deps", _qdrant_down)

    response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["deps"]["qdrant"] == "down"
    assert body["deps"]["db"] == "up"


async def test_health_is_not_wrapped_in_envelope(client: AsyncClient) -> None:
    """02 §3 的唯一例外：/health 不得出现 code/message/data/request_id 四个字段。"""
    response = await client.get("/health/live")

    body = response.json()
    for forbidden in ("code", "message", "data", "request_id"):
        assert forbidden not in body


async def test_ready_returns_503_when_dep_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """compose 的 healthcheck 打的就是这个端点，语义必须与 /health 一致。"""

    async def _db_down() -> dict[str, str]:
        return {"db": "down", "qdrant": "up", "llm": "up"}

    monkeypatch.setattr("app.api.v1.health.collect_deps", _db_down)

    response = await client.get("/health/ready")

    assert response.status_code == 503
