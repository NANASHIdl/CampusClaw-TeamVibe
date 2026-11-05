"""认证与会话业务。

规范依据：
- docs/specs/03-安全开发规范.md §5 §10
- specs/identity/spec.md ID-02 … ID-13

三件事在这里判定，路由层不做判断：
1. 口令比对（bcrypt）；
2. `(email, ip)` 失败计数与锁定；
3. 会话的建立与吊销，以及「当前请求属于谁、能看到哪个班」。

`class_id` 只从 `auth_sessions.class_id` 读出——这是 AGENTS.md §1.2 的落地位置。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.ids import new_ulid
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from app.models import AuthSession, LoginAttempt
from app.repositories import auth as auth_repo
from app.repositories import classes as classes_repo
from app.repositories import users as users_repo

logger = logging.getLogger(__name__)

# 登录失败的统一文案：不区分「用户不存在」与「口令错误」（ID-03）
LOGIN_FAILED_MESSAGE = "邮箱或口令不正确"

# 防用户枚举的耗时对齐：用户不存在时也做一次等价的 bcrypt 比对。
# 代价是启动时多算 ~250 ms，换来的是「两种情况耗时差 < 200 ms」这条判据成立。
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


@dataclass(frozen=True, slots=True)
class Principal:
    """当前登录主体。角色与班级来自服务端会话，不看任何请求声明。"""

    user_id: str
    display_name: str
    class_id: str | None
    role: str
    classes: tuple[tuple[str, str, str], ...]  # (class_id, name, role)


@dataclass(frozen=True, slots=True)
class LoginResult:
    principal: Principal
    token: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(moment: datetime) -> datetime:
    """把数据库读回的时间统一成 UTC aware。

    为什么需要：PostgreSQL 的 `TIMESTAMPTZ` 读回来是 aware，而 SQLite 的 `DATETIME`
    不保存时区、读回来是 naive。同一个比较必须在这两种后端上都成立——否则就会出现
    「本地冒烟能跑、换库才炸」或者反过来的情况，两种都属于隐蔽故障。
    naive 值按 UTC 解释（写入时用的就是 `datetime.now(UTC)`）。
    """
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _lock_remaining_seconds(attempt: LoginAttempt) -> int:
    if attempt.locked_until is None:
        return 0
    remaining = (_as_utc(attempt.locked_until) - _now()).total_seconds()
    return max(int(remaining) + 1, 0)


async def _build_principal(
    session: AsyncSession, user_id: str, display_name: str, class_id: str | None
) -> Principal:
    memberships = await classes_repo.list_user_classes(session, user_id)
    classes = tuple((room.id, room.name, membership.role) for membership, room in memberships)
    role = "student"
    for row_class_id, _name, row_role in classes:
        if row_class_id == class_id:
            role = row_role
            break
    return Principal(
        user_id=user_id,
        display_name=display_name,
        class_id=class_id,
        role=role,
        classes=classes,
    )


async def login(session: AsyncSession, email: str, password: str, ip: str) -> LoginResult:
    settings = get_settings()
    attempt = await auth_repo.get_attempt(session, email, ip)

    if (
        attempt is not None
        and attempt.locked_until is not None
        and _as_utc(attempt.locked_until) > _now()
    ):
        remaining = _lock_remaining_seconds(attempt)
        logger.warning("login_locked", extra={"email_masked": _mask(email), "ip": ip})
        raise ApiError(ErrorCode.RATE_LIMITED, f"尝试过于频繁，请 {remaining} 秒后再试")

    user = await users_repo.get_by_email(session, email)
    password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not user.is_active or not password_ok:
        await _record_failure(session, attempt, email, ip)
        logger.warning("login_failed", extra={"email_masked": _mask(email), "ip": ip})
        raise ApiError(ErrorCode.UNAUTHENTICATED, LOGIN_FAILED_MESSAGE)

    # 成功即清零，锁定也随之解除（ID-05）
    if attempt is not None:
        attempt.fail_count = 0
        attempt.locked_until = None

    memberships = await classes_repo.list_user_classes(session, user.id)
    class_id = memberships[0][0].class_id if memberships else None

    token = new_session_token()
    expires_at = _now() + timedelta(minutes=settings.SESSION_TTL_MINUTES)
    session.add(
        AuthSession(
            id=new_ulid(),
            user_id=user.id,
            class_id=class_id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
            ip=ip,
        )
    )
    await session.commit()

    principal = await _build_principal(session, user.id, user.display_name, class_id)
    logger.info("login_succeeded", extra={"user_id": user.id, "class_id": class_id})
    return LoginResult(principal=principal, token=token, expires_at=expires_at)


async def _record_failure(
    session: AsyncSession, attempt: LoginAttempt | None, email: str, ip: str
) -> None:
    settings = get_settings()
    if attempt is None:
        attempt = LoginAttempt(id=new_ulid(), email=email, ip=ip, fail_count=1, locked_until=None)
        session.add(attempt)
    else:
        attempt.fail_count += 1

    if attempt.fail_count >= settings.LOGIN_MAX_FAILS:
        attempt.locked_until = _now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
        logger.warning(
            "login_locked_now",
            extra={"email_masked": _mask(email), "ip": ip, "fail_count": attempt.fail_count},
        )
    await session.commit()


async def logout(session: AsyncSession, token: str) -> None:
    """注销即服务端吊销：删掉会话行，旧令牌立刻不可用（ID-07）。"""
    await auth_repo.delete_by_token_hash(session, hash_session_token(token))
    await session.commit()


async def resolve_principal(session: AsyncSession, token: str) -> Principal | None:
    """由令牌还原当前主体。会话不存在 / 已过期一律返回 None（由 deps 转 401）。"""
    if not token:
        return None

    record = await auth_repo.get_by_token_hash(session, hash_session_token(token))
    if record is None:
        return None

    if _as_utc(record.expires_at) <= _now():
        # 过期的行顺手清掉，避免表无限增长（ID-13）
        await auth_repo.delete_by_token_hash(session, record.token_hash)
        await session.commit()
        logger.info("session_expired", extra={"user_id": record.user_id})
        return None

    user = await users_repo.get_by_id(session, record.user_id)
    if user is None or not user.is_active:
        return None

    return await _build_principal(session, user.id, user.display_name, record.class_id)


def _mask(email: str) -> str:
    """日志里只留首字母与域名（07 §5：学生邮箱需脱敏）。"""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"
