"""资料与切片。

字典条目：docs/data-dictionary.md § materials / chunks
`chunks.class_id` 是冗余租户列，检索时用于强制过滤——不是查询附加条件，是隔离的物理基础。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Material(TimestampMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_materials_size_positive"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_materials_status",
        ),
        Index("ix_materials_class_created", "class_id", "created_at", "id"),
        Index("ix_materials_class_status", "class_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(80), nullable=False)
    mime: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    failure_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Chunk(TimestampMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("material_id", "chunk_index", name="uq_chunks_material_index"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_index_non_negative"),
        CheckConstraint("char_start >= 0", name="ck_chunks_char_start"),
        Index("ix_chunks_class", "class_id"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    material_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[str] = mapped_column(String(26), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 原文区间，用于「回溯到哪一段」（第 4 课要求：可回到材料、切片序号与字符区间）
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
