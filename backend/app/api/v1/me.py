"""当前用户路由。

准入声明：需登录（`get_current_user`）。角色与班级全部来自服务端会话，
请求头里的 `X-Role` 之类一概不看（ID-09）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.core.deps import CurrentUser
from app.core.errors import success
from app.schemas import ClassBrief, MeOut

router = APIRouter(tags=["identity"])


@router.get("/me", summary="当前用户信息")
async def read_me(request: Request, principal: CurrentUser) -> dict[str, Any]:
    body = MeOut(
        id=principal.user_id,
        display_name=principal.display_name,
        role=principal.role,
        class_id=principal.class_id,
        classes=[ClassBrief(id=cid, name=name, role=role) for cid, name, role in principal.classes],
    )
    return success(request, body)
