"""跨层依赖注入：会话解析、准入判定、数据库会话。

放在 core/ 而不是 api/：core 可被任意层依赖，而 api/ 直接 import repositories/
会被 `make layout` 判为反向依赖（02 §1）。

三条判定都在这里落地：
- 未登录 → 401 `1101`；
- 角色不足 → 404 `1202`（与「资源不存在」逐字节一致，不用 403，见 AGENTS.md §1.1）；
- `class_id` 只从 `auth_sessions` 读出，请求里的任何 `class_id` 都不采信。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.logging import get_logger
from app.repositories.base import session_scope
from app.services.auth import Principal, resolve_principal

logger = get_logger(module="api")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """一个请求一个会话。事务由 services/ 控制（02 §5）。"""
    async with session_scope() as session:
        yield session


def session_cookie_name() -> str:
    return get_settings().SESSION_COOKIE_NAME


def get_session_token(request: Request) -> str:
    """令牌只从 HttpOnly Cookie 取；不读 Authorization、不读 query（03 §5）。"""
    return request.cookies.get(session_cookie_name(), "")


async def get_current_user(request: Request) -> Principal:
    """解析当前登录主体。会话不存在 / 过期一律 401 `1101`。"""
    token = get_session_token(request)
    if not token:
        raise ApiError(ErrorCode.UNAUTHENTICATED)

    async with session_scope() as session:
        principal = await resolve_principal(session, token)

    if principal is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED)

    # 供访问日志记录，不参与任何判定
    request.state.user_id = principal.user_id
    request.state.class_id = principal.class_id
    return principal


CurrentUser = Annotated[Principal, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

RoleDependency = Callable[[CurrentUser], Awaitable[Principal]]


def require_role(role: str) -> RoleDependency:
    """教师端接口的准入。角色来自会话，不看 `X-Role` 之类的声明（03 §2）。"""

    async def _dependency(principal: CurrentUser) -> Principal:
        if principal.role != role:
            logger.warning(
                "role_denied",
                module="api",
                required_role=role,
                actual_role=principal.role,
                user_id=principal.user_id,
            )
            raise ApiError(ErrorCode.INSUFFICIENT_ROLE)
        return principal

    return _dependency


TeacherOnly = Annotated[Principal, Depends(require_role("teacher"))]
