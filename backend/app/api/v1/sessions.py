"""提问与会话路由（骨架期空壳）。

准入声明：需登录（`get_current_user`），会话级还要求本人。
业务实现见 tasks.md 第 6 组（assistant）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import not_implemented

router = APIRouter(prefix="/sessions", tags=["assistant"])


@router.post("", summary="建会话", dependencies=[Depends(get_current_user)])
async def create_session() -> None:
    raise not_implemented("/api/v1/sessions")


@router.get("", summary="我的会话列表", dependencies=[Depends(get_current_user)])
async def list_sessions() -> None:
    raise not_implemented("/api/v1/sessions")


@router.get("/{session_id}", summary="会话详情", dependencies=[Depends(get_current_user)])
async def read_session(session_id: str) -> None:
    raise not_implemented("/api/v1/sessions/{id}")


@router.post(
    "/{session_id}/messages",
    summary="提问（SSE 流式）",
    dependencies=[Depends(get_current_user)],
)
async def create_message(session_id: str) -> None:
    raise not_implemented("/api/v1/sessions/{id}/messages")
