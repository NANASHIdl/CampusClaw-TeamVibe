"""登录会话与登录失败计数。

会话令牌在库中只有 SHA-256（`token_hash`），查询按哈希命中；原值只出现在 Cookie 里。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthSession, LoginAttempt
from app.repositories.base import affected_rows


async def create(session: AsyncSession, auth_session: AuthSession) -> None:
    session.add(auth_session)


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> AuthSession | None:
    result = await session.execute(select(AuthSession).where(AuthSession.token_hash == token_hash))
    return result.scalar_one_or_none()


async def delete_by_token_hash(session: AsyncSession, token_hash: str) -> int:
    result = await session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))
    return affected_rows(result)


async def delete_expired(session: AsyncSession, now: datetime | None = None) -> int:
    """清理过期会话。启动时跑一次，避免表无限增长（07 §6）。"""
    moment = now or datetime.now(UTC)
    result = await session.execute(delete(AuthSession).where(AuthSession.expires_at <= moment))
    return affected_rows(result)


async def get_attempt(session: AsyncSession, email: str, ip: str) -> LoginAttempt | None:
    result = await session.execute(
        select(LoginAttempt).where(LoginAttempt.email == email, LoginAttempt.ip == ip)
    )
    return result.scalar_one_or_none()


def add_attempt(session: AsyncSession, attempt: LoginAttempt) -> None:
    session.add(attempt)
