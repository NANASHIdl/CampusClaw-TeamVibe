"""切片读写与关键词检索。

关键词检索走两条路并取并集：
1. PostgreSQL 全文检索 `to_tsvector('simple', content) @@ plainto_tsquery('simple', q)`；
2. 子串匹配 `content ILIKE %gram%`（中文没有空格分词，全文检索对中文近乎失效，
   子串是必要的兜底——不是"顺便加一个"，没有它中文关键词就是查不出来）。
排序与打分在 services/retrieval.py 做，这里只负责把候选捞回来。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Material
from app.repositories.base import affected_rows

# 单次关键词候选上限：先粗排再精排，避免整表拉进内存
KEYWORD_CANDIDATE_LIMIT = 200


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def add_all(session: AsyncSession, rows: Sequence[Chunk]) -> None:
    session.add_all(list(rows))


async def list_by_material(
    session: AsyncSession, material_id: str, *, offset: int, limit: int
) -> list[Chunk]:
    result = await session.execute(
        select(Chunk)
        .where(Chunk.material_id == material_id)
        .order_by(Chunk.chunk_index.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_by_material(session: AsyncSession, material_id: str) -> int:
    result = await session.execute(delete(Chunk).where(Chunk.material_id == material_id))
    return affected_rows(result)


async def get_by_ids_in_class(
    session: AsyncSession, class_id: str, chunk_ids: Sequence[str]
) -> list[tuple[Chunk, str]]:
    """向量检索只拿到点 ID，正文与标题回关系库补。

    条件里同时带 `class_id`：即使向量库的 payload 过滤被绕过，这里也把不住班级的切片挡掉。
    """
    if not chunk_ids:
        return []
    result = await session.execute(
        select(Chunk, Material.title)
        .join(Material, Material.id == Chunk.material_id)
        .where(
            Chunk.id.in_(list(chunk_ids)),
            Chunk.class_id == class_id,
            Material.class_id == class_id,
            Material.status == "ready",
            Material.deleted_at.is_(None),
        )
    )
    return [(row[0], row[1]) for row in result.all()]


async def keyword_search(
    session: AsyncSession, class_id: str, grams: Sequence[str], limit: int = KEYWORD_CANDIDATE_LIMIT
) -> list[tuple[Chunk, str]]:
    """返回 (切片, 资料标题)。三重过滤：class_id、ready、未删除。"""
    if not grams:
        return []

    phrase = " ".join(grams)
    patterns = [f"%{_escape_like(gram)}%" for gram in grams]

    statement = (
        select(Chunk, Material.title)
        .join(Material, Material.id == Chunk.material_id)
        .where(
            Chunk.class_id == class_id,
            Material.class_id == class_id,
            Material.status == "ready",
            Material.deleted_at.is_(None),
        )
        .where(
            or_(
                func.to_tsvector("simple", Chunk.content).op("@@")(
                    func.plainto_tsquery("simple", phrase)
                ),
                *[Chunk.content.ilike(pattern) for pattern in patterns],
            )
        )
        .order_by(Material.created_at.desc(), Chunk.chunk_index.asc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return [(row[0], row[1]) for row in result.all()]
