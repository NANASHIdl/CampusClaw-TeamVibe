"""身份与会话路由（骨架期空壳）。

准入声明：`/auth/login` 免认证；`/auth/logout` 需登录。
业务实现见 tasks.md 第 2 组（identity）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_implemented

router = APIRouter(prefix="/auth", tags=["identity"])


@router.post("/login", summary="登录（免认证）")
async def login() -> None:
    raise not_implemented("/api/v1/auth/login")


@router.post("/logout", summary="注销", dependencies=[Depends(get_current_user)])
async def logout() -> None:
    raise not_implemented("/api/v1/auth/logout")
