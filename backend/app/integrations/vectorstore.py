"""Qdrant 向量库客户端。

只保存向量与几个编号，不保存正文——正文以 `chunks` 表为准，向量可整表重建（07 §7）。

点 ID 的写法：Qdrant 只接受无符号整数或 UUID，不认 ULID 字符串，所以点 ID 用
`ulid_to_uuid(chunk.id)`——同一个 128 位值的 UUID 写法。payload 里同时放 `chunk_id`
（ULID 原文），这样从向量点能直接回到 `chunks` 行，不需要额外映射表。

所有失败都转成 `1502`：向量库挂了不该表现成 500，也不该返回空结果冒充成功（RT-10）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.ids import ulid_to_uuid

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None
_probe_timeout_seconds = 2.0


@dataclass(frozen=True, slots=True)
class VectorPoint:
    chunk_id: str
    class_id: str
    material_id: str
    chunk_index: int
    vector: list[float]


@dataclass(frozen=True, slots=True)
class VectorHit:
    chunk_id: str
    material_id: str
    chunk_index: int
    score: float


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=get_settings().QDRANT_URL, timeout=5)
    return _client


def reset_client() -> None:
    """测试用：丢弃单例，下次重新建连。"""
    global _client
    _client = None


def _collection() -> str:
    return get_settings().QDRANT_COLLECTION


async def ensure_collection(dim: int | None = None) -> None:
    """建集合（不存在时）。维度以配置为准，改了维度必须重建集合。"""
    settings = get_settings()
    size = dim or settings.EMBEDDING_DIM
    client = get_client()
    try:
        exists = await client.collection_exists(_collection())
        if exists:
            return
        await client.create_collection(
            collection_name=_collection(),
            vectors_config=qmodels.VectorParams(size=size, distance=qmodels.Distance.COSINE),
        )
        logger.info("qdrant_collection_created", extra={"collection": _collection()})
    except Exception as exc:
        raise ApiError(ErrorCode.VECTOR_UNREACHABLE, "检索服务暂不可用，可改用关键词模式") from exc


async def upsert(points: list[VectorPoint]) -> None:
    if not points:
        return
    client = get_client()
    payload = [
        qmodels.PointStruct(
            id=ulid_to_uuid(point.chunk_id),
            vector=point.vector,
            payload={
                "chunk_id": point.chunk_id,
                "class_id": point.class_id,
                "material_id": point.material_id,
                "chunk_index": point.chunk_index,
            },
        )
        for point in points
    ]
    try:
        await client.upsert(collection_name=_collection(), points=payload, wait=True)
    except Exception as exc:
        raise ApiError(ErrorCode.VECTOR_UNREACHABLE, "检索服务暂不可用，可改用关键词模式") from exc


async def search(
    class_id: str, vector: list[float], *, limit: int, score_threshold: float
) -> list[VectorHit]:
    """向量检索。`class_id` 作为 payload 过滤条件强制带上（RT-04）。"""
    client = get_client()
    query_filter = qmodels.Filter(
        must=[qmodels.FieldCondition(key="class_id", match=qmodels.MatchValue(value=class_id))]
    )
    try:
        response = await client.query_points(
            collection_name=_collection(),
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
    except Exception as exc:
        raise ApiError(ErrorCode.VECTOR_UNREACHABLE, "检索服务暂不可用，可改用关键词模式") from exc

    hits: list[VectorHit] = []
    for point in response.points:
        payload = point.payload or {}
        chunk_id = str(payload.get("chunk_id", ""))
        material_id = str(payload.get("material_id", ""))
        if not chunk_id or not material_id:
            continue
        hits.append(
            VectorHit(
                chunk_id=chunk_id,
                material_id=material_id,
                chunk_index=int(payload.get("chunk_index", 0)),
                score=float(point.score),
            )
        )
    return hits


async def delete_by_material(material_id: str) -> None:
    client = get_client()
    try:
        await client.delete(
            collection_name=_collection(),
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="material_id", match=qmodels.MatchValue(value=material_id)
                        )
                    ]
                )
            ),
            wait=True,
        )
    except Exception as exc:
        raise ApiError(ErrorCode.VECTOR_UNREACHABLE, "检索服务暂不可用，可改用关键词模式") from exc


async def count_by_material(material_id: str) -> int:
    client = get_client()
    try:
        result = await client.count(
            collection_name=_collection(),
            count_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="material_id", match=qmodels.MatchValue(value=material_id)
                    )
                ]
            ),
            exact=True,
        )
    except Exception as exc:
        raise ApiError(ErrorCode.VECTOR_UNREACHABLE, "检索服务暂不可用，可改用关键词模式") from exc
    return int(result.count)


async def ping() -> bool:
    """健康检查用：只探可达性，不抛异常。"""
    client = get_client()
    try:
        await client.get_collections()
        return True
    except Exception:  # 探测失败一律视为 down，不能把健康检查带崩
        return False


async def wait_until_ready(attempts: int = 15, delay_seconds: float = 2.0) -> bool:
    """启动时等向量库可用。

    compose 的 `depends_on: service_started` 只保证容器进程起来了，Qdrant 真正能接受
    请求还要几秒。首启时种子资料的入库正好落在这个窗口里，等一等比让它判失败划算。
    """
    import asyncio

    for _ in range(max(attempts, 1)):
        if await ping():
            return True
        await asyncio.sleep(delay_seconds)
    logger.warning("qdrant_not_ready", extra={"attempts": attempts})
    return False
