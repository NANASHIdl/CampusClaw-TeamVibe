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
    """启停钩子。启动时做四件幂等的事，停机时释放连接池（05 §3）。"""
    logger.info(
        "app_started",
        module="api",
        version=_settings.APP_VERSION,
        commit=_settings.APP_COMMIT,
        env=_settings.APP_ENV,
    )
    await _bootstrap()
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("shutdown_complete", module="api")


async def _bootstrap() -> None:
    """启动自检。

    每一步都单独兜住异常：数据库还没迁移、向量库还没起来时，服务仍要能启动，
    让 `/health` 如实报 `down`，而不是让容器反复重启（05 §3）。
    """
    import asyncio
    from pathlib import Path

    from app.core.config import get_settings
    from app.integrations import vectorstore
    from app.repositories import auth as auth_repo
    from app.repositories.base import session_scope
    from app.services import ingest as ingest_service
    from app.services import seed as seed_service

    settings = get_settings()

    try:
        await asyncio.to_thread(Path(settings.UPLOAD_DIR).mkdir, parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("upload_dir_unavailable", module="api", reason=str(exc))

    try:
        # 先等向量库就绪，再灌种子：首启时 Qdrant 往往还要几秒才能接受请求
        await vectorstore.wait_until_ready()
        async with session_scope() as session:
            await auth_repo.delete_expired(session)
            await session.commit()
        await ingest_service.recover_pending()
        await seed_service.ensure_seed_data()
        await ingest_service.retry_pending()
    except Exception as exc:  # 数据库未就绪：记录后继续启动，健康检查会报 down
        logger.warning("bootstrap_db_skipped", module="api", reason=type(exc).__name__)

    try:
        await vectorstore.ensure_collection()
    except Exception as exc:  # 向量库未就绪同理，不阻断启动
        logger.warning("bootstrap_qdrant_skipped", module="api", reason=type(exc).__name__)


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
