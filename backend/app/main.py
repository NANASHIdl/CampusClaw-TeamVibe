"""后端入口。装配顺序：Settings → 日志 → 中间件 → 异常处理器 → 路由。

规范依据：
- docs/specs/02-后端开发规范.md §1（main.py 职责）、§3（统一响应）
- docs/specs/05-部署运维规范.md §3（优雅停机 30 秒）
- openspec/changes/2026-10-28-bootstrap-skeleton/tasks.md 1.10

启动即校验配置：缺必填键时 load_settings() 会打一行 JSON 到 stderr 并 SystemExit(1)，
不会带着默认值继续跑（PC-02 / PC-03）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings, load_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.repositories.base import dispose_engine

# 1) 配置：缺失即退出，不进入后续步骤
_settings = load_settings()

# 2) 日志：在装配任何组件之前，保证后续每一步都能打结构化日志
configure_logging(_settings.LOG_LEVEL, console=_settings.LOG_FORMAT == "console")
logger = get_logger(module="api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """启停钩子。停机时释放连接池并记 shutdown_complete（05 §3）。"""
    logger.info(
        "app_started",
        module="api",
        version=_settings.APP_VERSION,
        commit=_settings.APP_COMMIT,
        env=_settings.APP_ENV,
    )
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("shutdown_complete", module="api")


def create_app() -> FastAPI:
    """应用工厂。测试可以多次调用，不污染模块级状态。"""
    settings = get_settings()

    app = FastAPI(
        title="CampusClaw · TeamVibe",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # 3) 中间件：request_id 继承/生成 → 日志上下文 → 回写响应头 → 计时
    app.add_middleware(RequestIDMiddleware)

    # 4) 异常处理器：所有失败都从统一信封出去
    register_exception_handlers(app)

    # 5) 路由：健康检查免认证且不走信封；业务路由挂在 /api/v1
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
