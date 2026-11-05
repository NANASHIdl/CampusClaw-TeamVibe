"""班级与成员读写。

`get_membership(class_id, user_id)` 把两个条件写在同一条查询里——这是本项目
「fetch-then-check」的落地形式：查不到就是查不到，不在业务层「先查班再判断关系」。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClassRoom, Membership, User


async def get_class(session: AsyncSession, class_id: str) -> ClassRoom | None:
    result = await session.execute(select(ClassRoom).where(ClassRoom.id == class_id))
    return result.scalar_one_or_none()


async def get_class_by_join_code(session: AsyncSession, join_code: str) -> ClassRoom | None:
    result = await session.execute(select(ClassRoom).where(ClassRoom.join_code == join_code))
    return result.scalar_one_or_none()


async def get_class_by_name(session: AsyncSession, name: str) -> ClassRoom | None:
    result = await session.execute(select(ClassRoom).where(ClassRoom.name == name))
    return result.scalar_one_or_none()


async def get_membership(session: AsyncSession, class_id: str, user_id: str) -> Membership | None:
    result = await session.execute(
        select(Membership).where(Membership.class_id == class_id, Membership.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_user_classes(
    session: AsyncSession, user_id: str
) -> list[tuple[Membership, ClassRoom]]:
    """当前用户的全部班级，按加入时间升序（第一条即登录时选定的主班级）。"""
    result = await session.execute(
        select(Membership, ClassRoom)
        .join(ClassRoom, ClassRoom.id == Membership.class_id)
        .where(Membership.user_id == user_id)
        .order_by(Membership.created_at.asc(), Membership.id.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def list_members(session: AsyncSession, class_id: str) -> list[tuple[User, str]]:
    result = await session.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.class_id == class_id)
        .order_by(Membership.role.asc(), User.display_name.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def count_members(session: AsyncSession, class_id: str) -> int:
    result = await session.execute(
        select(func.count()).select_from(Membership).where(Membership.class_id == class_id)
    )
    return int(result.scalar_one())


def add_class(session: AsyncSession, classroom: ClassRoom) -> None:
    session.add(classroom)


def add_membership(session: AsyncSession, membership: Membership) -> None:
    session.add(membership)
