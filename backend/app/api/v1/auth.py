"""身份与会话路由。

准入声明：`/auth/login` **免认证**（不挂任何依赖，且不读会话）；
`/auth/logout` 需登录（`get_current_user`）。
令牌只走 HttpOnly Cookie，响应体里永远不出现令牌原值（03 §5、ID-02）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import get_settings
from app.core.deps import DbSession, get_current_user, get_session_token, session_cookie_name
from app.core.errors import ApiError, ErrorCode, success
from app.schemas import ClassBrief, LoginIn, LoginOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["identity"])


def _client_ip(request: Request) -> str:
    """失败计数按 (email, ip) 计。只有反向代理会写 X-Forwarded-For，api 端口不对外映射。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/login", summary="登录（免认证）")
async def login(
    payload: LoginIn, request: Request, response: Response, session: DbSession
) -> dict[str, Any]:
    result = await auth_service.login(session, payload.email, payload.password, _client_ip(request))

    settings = get_settings()
    response.set_cookie(
        key=session_cookie_name(),
        value=result.token,
        max_age=settings.SESSION_TTL_MINUTES * 60,
        httponly=True,
        samesite="lax",
        # 生产强制 Secure；本地是 http://localhost:8080，带上会导致浏览器不保存 Cookie
        secure=settings.APP_ENV == "prod",
        path="/",
    )

    principal = result.principal
    body = LoginOut(
        id=principal.user_id,
        display_name=principal.display_name,
        role=principal.role,
        class_id=principal.class_id,
        classes=[ClassBrief(id=cid, name=name, role=role) for cid, name, role in principal.classes],
    )
    return success(request, body)


@router.post(
    "/logout",
    summary="注销（注销即服务端吊销，旧令牌立刻失效）",
    dependencies=[Depends(get_current_user)],
)
async def logout(request: Request, response: Response, session: DbSession) -> dict[str, Any]:
    token = get_session_token(request)
    if not token:
        raise ApiError(ErrorCode.UNAUTHENTICATED)
    await auth_service.logout(session, token)
    response.delete_cookie(key=session_cookie_name(), path="/")
    return success(request, {"logged_out": True})
