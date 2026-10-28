"""未知路径与错误信封用例。

覆盖的 Scenario：
- PC-05 未知路径返回 404 与登记错误码 1301
- PC-04 成功与失败共用 {code,message,data,request_id} 外层结构
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_unknown_route_returns_1301_envelope(client: AsyncClient) -> None:
    """PC-05：未知路径不暴露路由是否存在，按「资源不存在」统一返回。"""
    response = await client.get("/api/v1/not-exist-route")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 1301
    assert body["message"] == "资源不存在"
    assert body["data"] is None
    assert len(body["request_id"]) == 26


async def test_request_id_header_is_inherited_when_valid(client: AsyncClient) -> None:
    """PC-08：合法 X-Request-ID 原样继承，并写进响应体与响应头。"""
    given = "01HQ7Z3K9V2M4T8R6B1C0X5DNP"

    response = await client.get("/health/live", headers={"X-Request-ID": given})

    assert response.headers["X-Request-ID"] == given


async def test_invalid_request_id_is_replaced(client: AsyncClient) -> None:
    """PC-09：非法 X-Request-ID 被替换成新 ULID，不透传注入内容。"""
    response = await client.get(
        "/health/live", headers={"X-Request-ID": "<script>alert(1)</script>"}
    )

    assert response.status_code == 200
    returned = response.headers["X-Request-ID"]
    assert returned != "<script>alert(1)</script>"
    assert len(returned) == 26
    assert "<script>" not in returned
