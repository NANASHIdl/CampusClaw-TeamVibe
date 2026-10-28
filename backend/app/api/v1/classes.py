"""班级与成员路由（骨架期空壳）。

准入声明：建班需教师（`require_role`），其余需登录（`get_current_user`）。
业务实现见 tasks.md 第 3 组（classroom）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, require_role
from app.core.errors import not_implemented

router = APIRouter(prefix="/classes", tags=["classroom"])


@router.get("", summary="当前用户可见班级列表", dependencies=[Depends(get_current_user)])
async def list_classes() -> None:
    raise not_implemented("/api/v1/classes")


@router.post("", summary="教师建班", dependencies=[Depends(require_role)])
async def create_class() -> None:
    raise not_implemented("/api/v1/classes")


@router.post("/join", summary="学生凭入班码加入", dependencies=[Depends(get_current_user)])
async def join_class() -> None:
    raise not_implemented("/api/v1/classes/join")


@router.get(
    "/{class_id}/members",
    summary="本班成员列表",
    dependencies=[Depends(get_current_user)],
)
async def list_members(class_id: str) -> None:
    raise not_implemented("/api/v1/classes/{id}/members")
