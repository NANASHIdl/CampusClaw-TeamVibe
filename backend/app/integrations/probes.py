"""出站依赖探测：只查可达性，不做业务调用。

规范依据：
- docs/specs/02-后端开发规范.md §1（出站调用只允许在 integrations/）
- docs/specs/05-部署运维规范.md §3（依赖探测各 2 秒超时；llm 只查可达性，不发起计费调用）
- specs/platform-core/spec.md 的 PC-12 / PC-13
"""

from __future__ import annotations

import httpx

PROBE_TIMEOUT_SECONDS = 2.0


async def probe_http(url: str) -> bool:
    """GET 一次给定地址，能拿到任意 HTTP 响应即视为可达。

    只要服务活着就算 up：4xx 说明对端在跑（例如 Qdrant 的根路径可能返回 404），
    只有连不上、超时、或 5xx 才算 down。
    """
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        return response.status_code < 500
    except Exception:  # noqa: BLE001 - 探测失败一律视为 down
        return False


async def probe_qdrant(base_url: str) -> bool:
    """Qdrant 探活：根路径返回版本信息，不涉及集合与向量。"""
    return await probe_http(base_url.rstrip("/") + "/")


async def probe_llm(base_url: str) -> bool:
    """模型服务探活：只打根路径。

    **不得**调用 /chat/completions 之类的计费接口（05 §3 明确要求）。
    """
    return await probe_http(base_url.rstrip("/") + "/models")
