"""跨层依赖注入。

放在 core/ 而不是 api/：core 可被任意层依赖，而 api/ 直接 import repositories/
会被 `make layout` 判为反向依赖（02 §1）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import session_scope


@dataclass(frozen=True, slots=True)
class Principal:
    """当前登录主体。第 2 组（identity）落地后由真实会话填充。"""

    user_id: str
    role: str
    class_id: str | None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """一个请求一个会话。骨架期无业务查询，供后续能力复用。"""
    async with session_scope() as session:
        yield session


async def get_current_user() -> Principal | None:
    """会话校验的占位实现。

    骨架期一律返回 None 且不阻断请求，这样 `GET /api/v1/materials` 能走到空壳路由
    返回 501（PC-15），而不是先被 401 拦住。第 2 组会用真实实现替换本函数体，
    签名与依赖声明不变，路由文件无需改动。

    真实实现要求（tasks.md 2.2–2.5）：
    - 从 HttpOnly Cookie 读会话令牌，**不从 query / body / header 取 class_id**（AGENTS.md §1.2）；
    - 会话不存在或过期 → 401 `1101`。
    """
    return None


async def require_role(role: str) -> None:
    """角色判定的占位实现。第 2 组落地；现在不做拦截。

    角色不足时必须返回 404 `1202`（与 1301 逐字节一致），不得返回 403。
    """
    return None
