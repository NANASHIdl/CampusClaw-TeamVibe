"""请求标识中间件：继承或生成 X-Request-ID → 绑定日志上下文 → 回写响应头 → 计时。

规范依据：
- docs/specs/02-后端开发规范.md §9
- docs/specs/05-部署运维规范.md §4（request_id 必填，与响应头一致）
- specs/platform-core/spec.md 的 PC-08 / PC-09

写成纯 ASGI 中间件而不是 BaseHTTPMiddleware：后者会把响应包成流，第 6 组的 SSE
（`POST /sessions/{id}/messages`）会被缓冲，届时还要再改一遍。
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.ids import is_valid_ulid, new_ulid
from app.core.logging import get_logger

logger = get_logger(module="api")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """给每个 HTTP 请求分配 request_id，并记录一条访问日志。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        # 只继承格式合法的值；非法值一律替换，避免注入进日志与响应头（PC-09）
        request_id = incoming if is_valid_ulid(incoming) else new_ulid()

        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request_done",
                module="api",
                route=scope.get("path", ""),
                status=status_code,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
            )
            structlog.contextvars.clear_contextvars()


def request_id_from_scope(scope: dict[str, Any]) -> str | None:
    """从 ASGI scope 取 request_id；供非 HTTP 入口（如后台任务）复用。"""
    state = scope.get("state") or {}
    return state.get("request_id")
