"""班级与成员表。

字典条目：docs/data-dictionary.md § classes / memberships
`memberships` 的唯一索引是入班幂等的唯一依据（02 §6），不在应用层「先查再插」。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ClassRoom(TimestampMixin, Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    # 入班码：8 位大写字母 + 数字，敏感级「敏感」
    join_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Membership(TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("class_id", "user_id", name="uq_memberships_class_user"),
        CheckConstraint("role IN ('teacher', 'student')", name="ck_memberships_role"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
