"""资料与切片的出参（入参是 multipart，不走 Pydantic 模型）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChunkOut(BaseModel):
    chunk_index: int
    content: str
    char_count: int
    char_start: int
    char_end: int


class MaterialOut(BaseModel):
    id: str
    title: str
    original_filename: str
    mime: str
    size_bytes: int
    status: str
    failure_reason: str | None
    chunk_count: int
    created_at: datetime


class MaterialDetailOut(MaterialOut):
    chunks: list[ChunkOut]


class MaterialPageOut(BaseModel):
    """02 §8：分页响应必须带 total / page / page_size，且排序带唯一兜底键。"""

    total: int
    page: int
    page_size: int
    items: list[MaterialOut]


class MaterialDeleteOut(BaseModel):
    id: str
    deleted_at: datetime
