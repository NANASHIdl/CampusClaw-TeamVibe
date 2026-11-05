"""三模式检索与出处回填。

第 4 课的三条判据对应这里的三个分支：

- 模式可区分且可降级：`keyword` 只读关系库，不产生查询向量；`vector` 只打 Qdrant；
  `hybrid` 两路并发后融合。Qdrant 不可达时 `keyword` 照常返回，另外两条抛 1502。
- 班级边界不随请求改变：`class_id` 只从 `principal`（服务端会话）来，参数里的
  `class_id` 根本不进入本函数签名。
- 无依据不生成：`hits` 为空时返回固定文案，不用弱相关切片凑数。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.integrations import vectorstore
from app.integrations.embedding import embed_query
from app.repositories import chunks as chunks_repo
from app.repositories import classes as classes_repo
from app.services.auth import Principal

logger = logging.getLogger(__name__)

MODES = ("keyword", "vector", "hybrid")
DEFAULT_MODE = "hybrid"

# 无命中时的固定文案（RT-08）。这句话由服务端写死，不由模型生成。
NO_HIT_MESSAGE = "资料中未找到相关内容"

# RRF 的平滑常数，取文献常用值 60；只影响排序权重，不影响阈值判定
RRF_K = 60
# 关键词候选里参与打分的正文窗口
SNIPPET_WIDTH = 160
# 查询切gram 的上限，避免长句拼出上百个 OR 条件
MAX_GRAMS = 8


@dataclass(frozen=True, slots=True)
class Hit:
    material_id: str
    chunk_index: int
    title: str
    snippet: str
    score: float
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class SearchResult:
    mode: str
    hits: list[Hit]


def build_grams(query: str) -> list[str]:
    """把查询切成检索用的短语。

    中文不用空格分词，按二元组切是最省事且够用的办法：`主定理怎么用递归树证明`
    → `主定`、`定理`、`理怎`…，只要正文里出现相邻两字就能命中。
    同时保留整串，用于子串优先匹配与打分加权。
    """
    compact = "".join(query.split())
    grams: list[str] = []
    if len(compact) >= 2:
        for index in range(len(compact) - 1):
            gram = compact[index : index + 2]
            if gram not in grams:
                grams.append(gram)
    if compact and compact not in grams:
        grams.insert(0, compact)
    return grams[:MAX_GRAMS]


def make_snippet(content: str, query: str, width: int = SNIPPET_WIDTH) -> str:
    """截取包含关键词的窗口，而不是永远取开头——否则用户看不出为什么命中。"""
    compact = "".join(query.split())
    position = content.find(compact) if compact else -1
    if position == -1:
        for gram in build_grams(query):
            position = content.find(gram)
            if position != -1:
                break

    if position == -1:
        window = content[:width]
    else:
        start = max(position - width // 3, 0)
        window = content[start : start + width]

    snippet = window.strip()
    if len(content) > len(snippet):
        snippet = f"{snippet}…"
    return snippet


def _keyword_score(content: str, query: str, grams: list[str]) -> float:
    compact = "".join(query.split())
    if compact and compact in content:
        return 1.0
    if not grams:
        return 0.0
    matched = sum(1 for gram in grams if gram in content)
    return min(matched / len(grams), 0.99)


async def _require_class(session: AsyncSession, principal: Principal) -> str:
    """会话指向的班级必须存在，否则 404 1301——不能退化成「无命中」（RT-13）。"""
    if not principal.class_id:
        logger.warning("session_class_missing", extra={"user_id": principal.user_id})
        raise ApiError(ErrorCode.NOT_FOUND)
    room = await classes_repo.get_class(session, principal.class_id)
    if room is None:
        logger.warning(
            "session_class_missing",
            extra={"class_id": principal.class_id, "user_id": principal.user_id},
        )
        raise ApiError(ErrorCode.NOT_FOUND)
    return room.id


async def _keyword_hits(session: AsyncSession, class_id: str, query: str, limit: int) -> list[Hit]:
    grams = build_grams(query)
    rows = await chunks_repo.keyword_search(session, class_id, grams)
    hits: list[Hit] = []
    for chunk, title in rows:
        score = _keyword_score(chunk.content, query, grams)
        if score <= 0:
            continue
        hits.append(
            Hit(
                material_id=chunk.material_id,
                chunk_index=chunk.chunk_index,
                title=title,
                snippet=make_snippet(chunk.content, query),
                score=round(score, 4),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
        )
    hits.sort(key=lambda item: (-item.score, item.material_id, item.chunk_index))
    return hits[:limit]


async def _vector_hits(session: AsyncSession, class_id: str, query: str, limit: int) -> list[Hit]:
    settings = get_settings()
    vector = await embed_query(query)
    # 阈值与召回上限只从配置读（RT-06 / RT-07）
    raw = await vectorstore.search(
        class_id, vector, limit=limit, score_threshold=settings.SEARCH_VECTOR_MIN
    )
    if not raw:
        return []

    by_id = {
        chunk.id: (chunk, title)
        for chunk, title in await chunks_repo.get_by_ids_in_class(
            session, class_id, [hit.chunk_id for hit in raw]
        )
    }

    hits: list[Hit] = []
    for item in raw:
        found = by_id.get(item.chunk_id)
        if found is None:
            # 向量库里有、关系库里没有：派生数据过期，跳过并留一条日志
            logger.warning("vector_orphan", extra={"chunk_id": item.chunk_id, "class_id": class_id})
            continue
        chunk, title = found
        hits.append(
            Hit(
                material_id=chunk.material_id,
                chunk_index=chunk.chunk_index,
                title=title,
                snippet=make_snippet(chunk.content, query),
                score=round(item.score, 4),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
        )
    return hits


def _fuse(keyword: list[Hit], vector: list[Hit], limit: int) -> list[Hit]:
    """RRF（Reciprocal Rank Fusion）：按名次而非分数融合。

    关键词分与余弦相似度不在同一个量纲上，直接加权相加是错的。RRF 只看名次：
    `score = Σ 1/(K + rank)`，两种检索都排前面的切片自然浮上来。
    输出再做一次按最大值的归一化，使 `score` 落在 0–1，前端可以当相关度显示。
    """
    merged: dict[tuple[str, int], Hit] = {}
    accumulated: dict[tuple[str, int], float] = {}

    for ranked in (keyword, vector):
        for rank, hit in enumerate(ranked, start=1):
            key = (hit.material_id, hit.chunk_index)
            merged.setdefault(key, hit)
            accumulated[key] = accumulated.get(key, 0.0) + 1.0 / (RRF_K + rank)

    ordered = sorted(accumulated.items(), key=lambda item: (-item[1], item[0]))
    if not ordered:
        return []

    best = ordered[0][1]
    results: list[Hit] = []
    for key, value in ordered[:limit]:
        hit = merged[key]
        results.append(
            Hit(
                material_id=hit.material_id,
                chunk_index=hit.chunk_index,
                title=hit.title,
                snippet=hit.snippet,
                score=round(value / best, 4),
                char_start=hit.char_start,
                char_end=hit.char_end,
            )
        )
    return results


async def search(
    session: AsyncSession, principal: Principal, query: str, mode: str = DEFAULT_MODE
) -> SearchResult:
    settings = get_settings()
    class_id = await _require_class(session, principal)
    limit = settings.SEARCH_TOP_K

    if mode == "keyword":
        hits = await _keyword_hits(session, class_id, query, limit)
    elif mode == "vector":
        hits = await _vector_hits(session, class_id, query, limit)
    elif mode == "hybrid":
        # 两路并发；任一外部依赖失败由异常处理器转成 1502，不在这里吞掉
        keyword_hits, vector_hits = await asyncio.gather(
            _keyword_hits(session, class_id, query, limit),
            _vector_hits(session, class_id, query, limit),
        )
        hits = _fuse(keyword_hits, vector_hits, limit)
    else:
        raise ApiError(ErrorCode.INVALID_ENUM, "mode 只接受 keyword/vector/hybrid")

    logger.info(
        "search_done",
        extra={
            "class_id": class_id,
            "mode": mode,
            "hits": len(hits),
            "query_len": len(query),
        },
    )
    return SearchResult(mode=mode, hits=hits)
