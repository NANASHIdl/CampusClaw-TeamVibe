"""用户读写。

规范依据：02 §5（SQL 只在这里）、02 §4（归属判定写进查询条件）
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def add(session: AsyncSession, user: User) -> None:
    session.add(user)
