"""持久层基础设施：会话工厂与连通性探测。

骨架期只放「怎么连」，不放任何业务查询（design.md §7）。

规范依据：docs/specs/02-后端开发规范.md §1 §5
- SQL 只出现在 repositories/，所以 ping_db 的 `SELECT 1` 落在这里；
- 事务边界在 services/，本文件不 commit / rollback。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# 依赖探测统一 2 秒超时（specs/platform-core PC-12 与 05 §3）
PROBE_TIMEOUT_SECONDS = 2.0


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """进程内单例引擎。建连接是惰性的，所以 import 时不连库。"""
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """一个用例一个会话。事务由 services/ 控制，这里只负责开关。"""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def ping_db() -> bool:
    """数据库连通性。返回 True/False，不抛异常——健康检查不能因为依赖挂了就崩。"""
    try:
        async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # 探测失败一律视为 down，不让健康检查崩掉
        return False


async def dispose_engine() -> None:
    """停机时释放连接池。"""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
