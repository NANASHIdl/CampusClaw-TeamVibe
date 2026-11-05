"""出参模型统一导出。"""

from __future__ import annotations

from app.schemas.classroom import (
    ClassCreateIn,
    ClassJoinIn,
    ClassOut,
    MemberListOut,
    MemberOut,
)
from app.schemas.identity import ClassBrief, LoginIn, LoginOut, MeOut
from app.schemas.material import (
    ChunkOut,
    MaterialDeleteOut,
    MaterialDetailOut,
    MaterialOut,
    MaterialPageOut,
)
from app.schemas.search import SearchHit, SearchOut

__all__ = [
    "ChunkOut",
    "ClassBrief",
    "ClassCreateIn",
    "ClassJoinIn",
    "ClassOut",
    "LoginIn",
    "LoginOut",
    "MaterialDeleteOut",
    "MaterialDetailOut",
    "MaterialOut",
    "MaterialPageOut",
    "MeOut",
    "MemberListOut",
    "MemberOut",
    "SearchHit",
    "SearchOut",
]
