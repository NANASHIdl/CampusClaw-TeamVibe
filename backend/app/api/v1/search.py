"""检索路由（骨架期空壳）。

准入声明：需登录（`get_current_user`）。业务实现见 tasks.md 第 5 组（retrieval）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_implemented

router = APIRouter(tags=["retrieval"])


@router.get("/search", summary="本班检索", dependencies=[Depends(get_current_user)])
async def search() -> None:
    raise not_implemented("/api/v1/search")
