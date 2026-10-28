"""骨架期空壳路由用例。

覆盖的 Scenario：
- PC-15 骨架期业务路由返回 501 + code=1500 + message="未实现"，且不是 404
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/materials"),
        ("GET", "/api/v1/me"),
        ("GET", "/api/v1/classes"),
        ("GET", "/api/v1/search"),
        ("GET", "/api/v1/sessions"),
    ],
)
async def test_stub_routes_return_501(
    client: AsyncClient, method: str, path: str
) -> None:
    """PC-15：未实现的能力返回 501 而不是 404，避免被误认为路由没挂上。"""
    response = await client.request(method, path)

    assert response.status_code == 501
    body = response.json()
    assert body["code"] == 1500
    assert body["message"] == "未实现"
    assert body["data"] is None
    assert len(body["request_id"]) == 26
    assert response.headers["X-Request-ID"] == body["request_id"]
