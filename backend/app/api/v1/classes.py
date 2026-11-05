"""班级与成员路由。

准入声明：建班需教师（`require_role("teacher")`），其余需登录（`get_current_user`）。
`class_id` 只作为路径参数用于「证明我是该班成员」，绝不作为数据过滤条件的来源。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.core.deps import CurrentUser, DbSession, TeacherOnly
from app.core.errors import success
from app.schemas import ClassCreateIn, ClassJoinIn, ClassOut, MemberListOut, MemberOut
from app.services import classroom as classroom_service

router = APIRouter(prefix="/classes", tags=["classroom"])


def _to_out(view: classroom_service.ClassView) -> ClassOut:
    return ClassOut(
        id=view.id,
        name=view.name,
        role=view.role,
        member_count=view.member_count,
        join_code=view.join_code,
    )


@router.get("", summary="当前用户可见班级列表")
async def list_classes(
    request: Request, session: DbSession, principal: CurrentUser
) -> dict[str, Any]:
    views = await classroom_service.list_classes(session, principal)
    return success(request, [_to_out(view) for view in views])


@router.post("", summary="教师建班（教师）")
async def create_class(
    payload: ClassCreateIn,
    request: Request,
    session: DbSession,
    principal: TeacherOnly,
) -> dict[str, Any]:
    view = await classroom_service.create_class(session, principal, payload.name)
    return success(request, _to_out(view), message="created")


@router.post("/join", summary="凭入班码加入（幂等）")
async def join_class(
    payload: ClassJoinIn, request: Request, session: DbSession, principal: CurrentUser
) -> dict[str, Any]:
    view = await classroom_service.join_class(session, principal, payload.join_code)
    return success(request, _to_out(view))


@router.get("/{class_id}/members", summary="本班成员列表")
async def list_members(
    class_id: str, request: Request, session: DbSession, principal: CurrentUser
) -> dict[str, Any]:
    members = await classroom_service.list_members(session, principal, class_id)
    body = MemberListOut(
        class_id=class_id,
        members=[
            MemberOut(user_id=user_id, display_name=name, role=role)
            for user_id, name, role in members
        ],
    )
    return success(request, body)
