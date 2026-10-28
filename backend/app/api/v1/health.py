"""健康检查端点。免认证，且**不走统一信封**。

规范依据：
- docs/specs/02-后端开发规范.md §3「唯一例外」条款
- docs/specs/05-部署运维规范.md §3
- specs/platform-core/spec.md 的 PC-12 / PC-13

为什么不套 {code,message,data,request_id}：探针与负载均衡只认 HTTP 状态码与固定字段，
套一层信封会让探针多一层解析，且 status 与 deps 必须能被 docker healthcheck 直接读到。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.logging import get_logger, utc_now_iso
from app.services.health import all_up, collect_deps

router = APIRouter(tags=["health"])
logger = get_logger(module="api")

# 依赖不可达时按 dep 映射到登记过的错误码（02 §3 的 15xx 区间）
_DEP_ERROR_CODE = {"db": 1503, "qdrant": 1502, "llm": 1501}


def _base_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "commit": settings.APP_COMMIT,
        "time": utc_now_iso(),
    }


async def _fill_deps(response: Response, payload: dict[str, Any]) -> dict[str, Any]:
    """探测依赖并写入 payload；任一 down 则把状态码改成 503，进程不退出。"""
    deps = await collect_deps()
    payload["deps"] = deps

    if all_up(deps):
        return payload

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    payload["status"] = "degraded"
    for dep, state in deps.items():
        if state != "up":
            logger.warning(
                "dep_unreachable",
                module="api",
                dep=dep,
                error_code=_DEP_ERROR_CODE.get(dep, 1503),
            )
    return payload


@router.get("/health/live", summary="进程存活（免认证，不查依赖）")
async def live() -> dict[str, Any]:
    """只看进程是否活着：不查任何依赖，永远 200。"""
    return _base_payload()


@router.get("/health/ready", summary="可接流量（免认证，依赖任一 down 即 503）")
async def ready(response: Response) -> dict[str, Any]:
    return await _fill_deps(response, _base_payload())


@router.get("/health", summary="综合体检（免认证，含版本与依赖明细）")
async def health(response: Response) -> dict[str, Any]:
    """综合体检：任一依赖不可达返回 503，但**进程不退出**（PC-13）。"""
    return await _fill_deps(response, _base_payload())
