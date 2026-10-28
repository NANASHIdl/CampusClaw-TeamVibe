"""`/api/v1` 路由汇总。

准入由各路由文件自行声明：`get_current_user`（需登录）、`require_role`（需教师）、
或 summary 标注「免认证」。本文件只做挂载，不承载任何准入判断。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, classes, materials, me, search, sessions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(classes.router)
api_router.include_router(materials.router)
api_router.include_router(search.router)
api_router.include_router(sessions.router)

__all__ = ["api_router"]
