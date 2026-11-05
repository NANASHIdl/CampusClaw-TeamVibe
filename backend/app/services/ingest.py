"""入库流水线：正文提取 → 切分 → 嵌入 → 向量入库 → ready。

为什么是后台任务而不是请求内同步做（02 §5、07 §7）：
1. 事务里不得夹带外部调用，嵌入与向量库都是外部调用；
2. 一份 800 KB 的讲义要切上千片，请求内做完会把页面卡住十几秒。

顺序固定为「切片入库 → 向量入库 → 置 ready」：中途失败时 `materials.status=failed`
并保留原因，切片与向量都会被清掉，检索看不到半成品（RT-09）。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.ids import new_ulid
from app.integrations import vectorstore
from app.integrations.embedding import embed_texts
from app.integrations.text_extract import EmptyTextError, UnsupportedFormatError, read_text_file
from app.models import Chunk
from app.repositories import chunks as chunks_repo
from app.repositories import materials as materials_repo
from app.repositories.base import session_scope
from app.services.chunking import split_text
from app.services.materials import storage_dir

logger = logging.getLogger(__name__)

_FAILURE_REASON_MAX = 200


def _reason(exc: Exception) -> str:
    if isinstance(exc, EmptyTextError):
        return "文件无可提取文本"
    if isinstance(exc, UnsupportedFormatError):
        return "文件格式暂不支持解析"
    if isinstance(exc, ApiError):
        return exc.message[:_FAILURE_REASON_MAX]
    return f"处理失败：{type(exc).__name__}"


async def _mark_failed(material_id: str, class_id: str, exc: Exception) -> None:
    async with session_scope() as session:
        await chunks_repo.delete_by_material(session, material_id)
        await materials_repo.set_status(
            session, material_id, class_id, "failed", failure_reason=_reason(exc), chunk_count=0
        )
        await session.commit()
    logger.warning(
        "ingest_failed",
        extra={"material_id": material_id, "reason": _reason(exc)},
    )


async def process_material(material_id: str, class_id: str) -> None:
    """把一份资料处理到 ready（或 failed）。可重复执行：已 ready 直接返回。"""
    settings = get_settings()

    async with session_scope() as session:
        material = await materials_repo.get_in_class(session, material_id, class_id)
        if material is None or material.status == "ready":
            return
        stored_filename = material.stored_filename
        await materials_repo.set_status(session, material_id, class_id, "processing")
        await session.commit()

    path = Path(storage_dir(class_id)) / stored_filename
    ext = stored_filename.rsplit(".", 1)[-1] if "." in stored_filename else ""

    try:
        # ---- 事务外：读文本、切分、嵌入 ----
        text = await asyncio.to_thread(read_text_file, path, ext)
        pieces = split_text(text, settings.CHUNK_SIZE_CHARS, settings.CHUNK_OVERLAP_CHARS)
        if not pieces:
            raise EmptyTextError("文件无可提取文本")

        vectors = await embed_texts([piece.content for piece in pieces])
        await vectorstore.ensure_collection(len(vectors[0]))

        # ---- 事务一：切片入库 ----
        rows = [
            Chunk(
                id=new_ulid(),
                material_id=material_id,
                class_id=class_id,
                chunk_index=piece.index,
                content=piece.content,
                char_count=len(piece.content),
                char_start=piece.char_start,
                char_end=piece.char_end,
            )
            for piece in pieces
        ]
        async with session_scope() as session:
            await chunks_repo.delete_by_material(session, material_id)
            chunks_repo.add_all(session, rows)
            await session.commit()

        # ---- 事务外：向量入库 ----
        await vectorstore.upsert(
            [
                vectorstore.VectorPoint(
                    chunk_id=row.id,
                    class_id=class_id,
                    material_id=material_id,
                    chunk_index=row.chunk_index,
                    vector=vector,
                )
                for row, vector in zip(rows, vectors, strict=True)
            ]
        )

        # ---- 事务二：置 ready ----
        async with session_scope() as session:
            await materials_repo.set_status(
                session, material_id, class_id, "ready", failure_reason=None, chunk_count=len(rows)
            )
            await session.commit()

        logger.info("ingest_done", extra={"material_id": material_id, "chunks": len(rows)})

    except Exception as exc:  # 任何失败都要让状态离开 processing
        if isinstance(exc, ApiError) and exc.code == ErrorCode.VECTOR_UNREACHABLE:
            # 向量库不可达是「依赖暂时不在」，不是「这份资料有问题」：
            # 退回 pending 等下次启动或重试，别把一份好讲义标成 failed。
            async with session_scope() as session:
                await chunks_repo.delete_by_material(session, material_id)
                await materials_repo.set_status(
                    session, material_id, class_id, "pending", failure_reason=None, chunk_count=0
                )
                await session.commit()
            logger.warning("ingest_deferred", extra={"material_id": material_id, "dep": "qdrant"})
            return

        try:
            await vectorstore.delete_by_material(material_id)
        except ApiError:
            logger.warning("ingest_vector_cleanup_failed", extra={"material_id": material_id})
        await _mark_failed(material_id, class_id, exc)


async def retry_pending(limit: int = 50) -> int:
    """启动补偿：把还停在 pending 的资料再处理一遍。

    典型场景是首次启动时向量库还没就绪——种子资料的入库被 defer 成 pending，
    下次启动应自动补上，而不是让人手工重传。
    """
    async with session_scope() as session:
        rows = await materials_repo.list_by_status(session, "pending", limit)

    for material_id, class_id in rows:
        await process_material(material_id, class_id)

    if rows:
        logger.info("ingest_retry_done", extra={"count": len(rows)})
    return len(rows)


async def delete_material_assets(material_id: str, class_id: str, stored_filename: str) -> None:
    """软删后的副本清理：切片 → 向量 → 文件（07 §6 的副本清单前 3 项）。"""
    async with session_scope() as session:
        await chunks_repo.delete_by_material(session, material_id)
        await session.commit()

    try:
        await vectorstore.delete_by_material(material_id)
    except ApiError:
        logger.warning("delete_vector_failed", extra={"material_id": material_id})

    path = Path(storage_dir(class_id)) / stored_filename
    try:
        await asyncio.to_thread(path.unlink, True)
    except OSError:
        logger.warning("delete_file_failed", extra={"path": str(path)})

    logger.info("material_assets_deleted", extra={"material_id": material_id})


async def recover_pending() -> None:
    """启动时把卡在 processing 超过 10 分钟的资料退回 pending（MT-07）。"""
    async with session_scope() as session:
        count = await materials_repo.reset_stale_processing(session, minutes=10)
        await session.commit()
    if count:
        logger.info("stale_processing_reset", extra={"count": count})
