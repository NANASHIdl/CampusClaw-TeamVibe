"""模型导出。Alembic 与业务层统一从这里取，避免漏 import 导致 metadata 不含表。"""

from __future__ import annotations

from app.models.auth import AuthSession, LoginAttempt
from app.models.base import Base, TimestampMixin
from app.models.classroom import ClassRoom, Membership
from app.models.material import Chunk, Material
from app.models.user import User

__all__ = [
    "AuthSession",
    "Base",
    "Chunk",
    "ClassRoom",
    "LoginAttempt",
    "Material",
    "Membership",
    "TimestampMixin",
    "User",
]
