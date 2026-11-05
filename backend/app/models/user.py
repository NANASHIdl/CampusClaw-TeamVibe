"""用户表。

字典条目：docs/data-dictionary.md § users
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # 登录名。敏感级「敏感」：接口与日志都不整串输出
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    # bcrypt(cost=12) 结果，长度 60；机密级，任何接口都不返回
    password_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
