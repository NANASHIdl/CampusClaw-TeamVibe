"""检索路由。

准入声明：需登录（`get_current_user`）。
`class_id` 不是本接口的参数——即使调用方拼上 `?class_id=...`，它也不会进入业务层，
这是 RT-05 的落地方式。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.core.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode, success
from app.schemas import SearchHit, SearchOut
from app.services import retrieval as retrieval_service

router = APIRouter(tags=["retrieval"])

QUERY_MIN = 2
QUERY_MAX = 200


@router.get("/search", summary="本班资料检索（keyword / vector / hybrid）")
async def search(
    request: Request,
    session: DbSession,
    principal: CurrentUser,
    q: str = Query(description="查询串，2–200 字符"),
    mode: str = Query(default=retrieval_service.DEFAULT_MODE),
) -> dict[str, Any]:
    query = q.strip()
    if len(query) < QUERY_MIN or len(query) > QUERY_MAX:
        # RT-11：空串、纯空白、超长都在入口挡掉，不触发检索
        raise ApiError(ErrorCode.INVALID_PARAM, f"查询串长度需在 {QUERY_MIN}–{QUERY_MAX} 字符之间")
    if mode not in retrieval_service.MODES:
        # RT-03：非法枚举必须报错，不得退化成默认模式
        raise ApiError(ErrorCode.INVALID_ENUM, "mode 只接受 keyword/vector/hybrid")

    result = await retrieval_service.search(session, principal, query, mode)
    body = SearchOut(
        mode=result.mode,
        hits=[
            SearchHit(
                material_id=hit.material_id,
                chunk_index=hit.chunk_index,
                title=hit.title,
                snippet=hit.snippet,
                score=hit.score,
                char_start=hit.char_start,
                char_end=hit.char_end,
            )
            for hit in result.hits
        ],
        total=len(result.hits),
        message=None if result.hits else retrieval_service.NO_HIT_MESSAGE,
    )
    return success(request, body)
