"""当前用户路由（骨架期空壳）。

准入声明：需登录（`get_current_user`）。业务实现见 tasks.md 第 2 组。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_implemented

router = APIRouter(tags=["identity"])


@router.get("/me", summary="当前用户信息", dependencies=[Depends(get_current_user)])
async def read_me() -> None:
    raise not_implemented("/api/v1/me")
