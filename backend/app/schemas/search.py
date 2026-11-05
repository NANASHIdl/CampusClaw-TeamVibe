"""检索的出参。

RT-01 的字段名是接口契约的一部分：`material_id / chunk_index / title / snippet / score`，
第 4 课另外要求能回到字符区间，所以带 `char_start / char_end`。
"""

from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    material_id: str
    chunk_index: int
    title: str
    snippet: str
    score: float
    char_start: int
    char_end: int


class SearchOut(BaseModel):
    mode: str
    hits: list[SearchHit]
    total: int
    # 无命中时的固定文案（RT-08）；有命中时为 null，前端不据此判断成功与否
    message: str | None = None
