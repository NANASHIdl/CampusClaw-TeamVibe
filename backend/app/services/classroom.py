"""班级与成员业务。

隔离的核心在这里：任何按 `class_id` 取数据的动作，都要先证明"当前用户是该班成员"，
而证明方式是 `get_membership(class_id, user_id)` 一条查询——查不到就是查不到。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.ids import new_ulid
from app.core.security import new_join_code
from app.models import ClassRoom, Membership
from app.repositories import classes as classes_repo
from app.services.auth import Principal

logger = logging.getLogger(__name__)

# 入班码冲突时的重试次数：8 位、32 字母表，实际碰撞概率可忽略，重试只是兜底
_JOIN_CODE_RETRIES = 5


@dataclass(frozen=True, slots=True)
class ClassView:
    id: str
    name: str
    role: str
    member_count: int
    join_code: str | None


async def list_classes(session: AsyncSession, principal: Principal) -> list[ClassView]:
    rows = await classes_repo.list_user_classes(session, principal.user_id)
    views: list[ClassView] = []
    for membership, room in rows:
        member_count = await classes_repo.count_members(session, room.id)
        views.append(
            ClassView(
                id=room.id,
                name=room.name,
                role=membership.role,
                member_count=member_count,
                # 只有本班教师看得到入班码；学生拿到就等于能拉人进来
                join_code=room.join_code if membership.role == "teacher" else None,
            )
        )
    return views


async def create_class(session: AsyncSession, principal: Principal, name: str) -> ClassView:
    if principal.role != "teacher":
        raise ApiError(ErrorCode.INSUFFICIENT_ROLE)

    room: ClassRoom | None = None
    for _ in range(_JOIN_CODE_RETRIES):
        candidate = ClassRoom(
            id=new_ulid(),
            name=name,
            join_code=new_join_code(),
            owner_id=principal.user_id,
        )
        session.add(candidate)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            continue
        room = candidate
        break

    if room is None:
        raise ApiError(ErrorCode.INTERNAL, "班级创建失败，请重试")

    session.add(
        Membership(id=new_ulid(), class_id=room.id, user_id=principal.user_id, role="teacher")
    )
    await session.commit()
    logger.info("class_created", extra={"class_id": room.id, "owner_id": principal.user_id})
    return ClassView(
        id=room.id, name=room.name, role="teacher", member_count=1, join_code=room.join_code
    )


async def join_class(session: AsyncSession, principal: Principal, join_code: str) -> ClassView:
    room = await classes_repo.get_class_by_join_code(session, join_code)
    if room is None:
        # 入班码错与班级不存在返回同一个 404，避免成为"班级枚举"工具
        raise ApiError(ErrorCode.NOT_FOUND)

    existing = await classes_repo.get_membership(session, room.id, principal.user_id)
    if existing is not None:
        # 幂等：已是成员时返回 200 与当前信息，不报 409（02 §6）
        member_count = await classes_repo.count_members(session, room.id)
        return ClassView(
            id=room.id,
            name=room.name,
            role=existing.role,
            member_count=member_count,
            join_code=room.join_code if existing.role == "teacher" else None,
        )

    session.add(
        Membership(id=new_ulid(), class_id=room.id, user_id=principal.user_id, role="student")
    )
    await session.commit()
    member_count = await classes_repo.count_members(session, room.id)
    logger.info("class_joined", extra={"class_id": room.id, "user_id": principal.user_id})
    return ClassView(
        id=room.id, name=room.name, role="student", member_count=member_count, join_code=None
    )


async def list_members(
    session: AsyncSession, principal: Principal, class_id: str
) -> list[tuple[str, str, str]]:
    """非本班成员与班级不存在都返回 404，响应一致（AGENTS.md §1.1）。"""
    membership = await classes_repo.get_membership(session, class_id, principal.user_id)
    if membership is None:
        raise ApiError(ErrorCode.NOT_FOUND)

    rows = await classes_repo.list_members(session, class_id)
    return [(user.id, user.display_name, role) for user, role in rows]
