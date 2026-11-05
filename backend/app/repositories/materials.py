"""资料读写。

关键约束（AGENTS.md §1.1）：取单条资源的查询同时带 `id` 与 `class_id`，
取不到即由 services/ 转成 1301，不存在「先查出来再判断归属」的写法。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Material
from app.repositories.base import affected_rows

# 排序白名单到列的映射；不在表里的字段在 services/ 就被 1005 拦掉（02 §4）。
SORT_COLUMNS = {
    "created_at": Material.created_at,
    "title": Material.title,
}


def add(session: AsyncSession, material: Material) -> None:
    session.add(material)


async def get_in_class(session: AsyncSession, material_id: str, class_id: str) -> Material | None:
    """本班未删除的资料。跨班与不存在返回同一个 None，调用方无从区分。"""
    result = await session.execute(
        select(Material).where(
            Material.id == material_id,
            Material.class_id == class_id,
            Material.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def count_active(session: AsyncSession, class_id: str) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Material)
        .where(Material.class_id == class_id, Material.deleted_at.is_(None))
    )
    return int(result.scalar_one())


def _page_statement(class_id: str, status: str | None, sort: str, order: str) -> Select[Any]:
    statement = select(Material).where(Material.class_id == class_id, Material.deleted_at.is_(None))
    if status:
        statement = statement.where(Material.status == status)
    column: Any = SORT_COLUMNS.get(sort, Material.created_at)
    # 唯一兜底键：created_at 相同的行靠 id 定序，翻页才不会重复或漏行（02 §8）
    if order == "asc":
        return statement.order_by(column.asc(), Material.id.asc())
    return statement.order_by(column.desc(), Material.id.desc())


async def list_page(
    session: AsyncSession,
    class_id: str,
    *,
    status: str | None,
    sort: str,
    order: str,
    offset: int,
    limit: int,
) -> list[Material]:
    statement = _page_statement(class_id, status, sort, order).offset(offset).limit(limit)
    result = await session.execute(statement)
    return [cast(Material, row) for row in result.scalars().all()]


async def count_page(session: AsyncSession, class_id: str, status: str | None) -> int:
    statement = (
        select(func.count())
        .select_from(Material)
        .where(Material.class_id == class_id, Material.deleted_at.is_(None))
    )
    if status:
        statement = statement.where(Material.status == status)
    result = await session.execute(statement)
    return int(result.scalar_one())


async def list_by_status(
    session: AsyncSession, status: str, limit: int = 50
) -> list[tuple[str, str]]:
    """按状态取待处理资料 (id, class_id)，供启动时的补偿重跑使用。"""
    result = await session.execute(
        select(Material.id, Material.class_id)
        .where(Material.status == status, Material.deleted_at.is_(None))
        .order_by(Material.created_at.asc())
        .limit(limit)
    )
    return [(str(row[0]), str(row[1])) for row in result.all()]


async def set_status(
    session: AsyncSession,
    material_id: str,
    class_id: str,
    status: str,
    *,
    failure_reason: str | None = None,
    chunk_count: int | None = None,
) -> None:
    values: dict[str, object] = {"status": status, "failure_reason": failure_reason}
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    await session.execute(
        update(Material)
        .where(Material.id == material_id, Material.class_id == class_id)
        .values(**values)
    )


async def soft_delete(session: AsyncSession, material_id: str, class_id: str) -> datetime:
    moment = datetime.now(UTC)
    await session.execute(
        update(Material)
        .where(
            Material.id == material_id,
            Material.class_id == class_id,
            Material.deleted_at.is_(None),
        )
        .values(deleted_at=moment)
    )
    return moment


async def reset_stale_processing(session: AsyncSession, minutes: int = 10) -> int:
    """启动时把「卡在 processing 超过 10 分钟」的资料退回 pending（MT-07 的状态机约定）。"""
    cutoff = datetime.now(UTC).timestamp() - minutes * 60
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=UTC)
    result = await session.execute(
        update(Material)
        .where(Material.status == "processing", Material.updated_at <= cutoff_dt)
        .values(status="pending")
    )
    return affected_rows(result)
