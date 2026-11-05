"""ORM 基类与公共列。

规范依据：docs/specs/07-数据规范.md §1 §2（主键 ULID、时间 UTC、审计字段）
主键一律 CHAR(26) ULID，由 `app.core.ids` 生成，不使用自增整数。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """全部模型的声明式基类；Alembic 用它取 metadata。"""


class TimestampMixin:
    """`created_at` / `updated_at`。`updated_at` 由 ORM onupdate 维护，业务代码不手写。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
