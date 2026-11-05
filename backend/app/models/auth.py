"""登录会话与登录失败计数。

字典条目：docs/data-dictionary.md § auth_sessions / login_attempts

`auth_sessions` 只存令牌的 SHA-256，不存原值——库被读走也无法直接冒用（07 §5 机密级）。
`login_attempts` 按 (email, ip) 计数，用于 ID-04 的「5 次锁 15 分钟」。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 登录当时选定的班级；班级只取自这一列，不从请求参数取（AGENTS.md §1.2）
    class_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False, default="")


class LoginAttempt(TimestampMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (UniqueConstraint("email", "ip", name="uq_login_attempts_email_ip"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    email: Mapped[str] = mapped_column(String(160), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False, default="")
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
