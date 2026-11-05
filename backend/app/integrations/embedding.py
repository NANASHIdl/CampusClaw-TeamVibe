"""嵌入客户端。

两种提供方，由 `EMBEDDING_BASE_URL` 是否为空决定：

1. **HTTP（真实嵌入服务）**：`{EMBEDDING_BASE_URL}/embeddings`，OpenAI 兼容格式。
   出站前按 03 §8 校验 host 白名单，不在名单内直接拒绝，不发请求。
2. **离线确定性嵌入**：字符二元组哈希到固定维度并做 L2 归一化。

第 2 种存在的理由不是"偷懒"：课程判据要求随时随地可复现，而把真实嵌入服务的密钥
写进 `.env.example` 或演示环境是不允许的（AGENTS.md §1.3）。离线嵌入没有语义理解能力，
它只能保证「同样的文本得到同样的向量、相近文本得到较高余弦相似度」这一条链路可跑通。
接真实服务时把 `EMBEDDING_BASE_URL` 填上即可，业务代码与阈值都不用改。
"""

from __future__ import annotations

import hashlib
import math
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode

# 单次请求的批量上限，避免一次塞几千条切片把网关打挂
EMBED_BATCH_SIZE = 32
_HTTP_TIMEOUT_SECONDS = 20.0


def _assert_allowed(url: str) -> None:
    """出站白名单（03 §8）。空名单视为"只允许配置里出现的两个 host"。"""
    settings = get_settings()
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = settings.allowed_outbound_hosts
    if allowed:
        if host in allowed:
            return
    else:
        configured = {
            urlparse(settings.EMBEDDING_BASE_URL).hostname,
            urlparse(settings.LLM_BASE_URL).hostname,
        }
        if host in configured:
            return
    raise ApiError(
        ErrorCode.LLM_UNREACHABLE,
        "嵌入服务不在出站白名单内",
    )


def _local_embed(text: str, dim: int) -> list[float]:
    """字符二元组哈希嵌入：确定性、无依赖、可离线复现。

    词袋模型的老办法：把每对相邻字符压进 `dim` 个桶，累加后 L2 归一化。
    中文按字切二元组，英文按小写字符切，足以让「同一段话」拿到相同向量。
    """
    normalized = text.lower().strip()
    buckets = [0.0] * dim
    if not normalized:
        return buckets

    grams = [normalized[i : i + 2] for i in range(max(len(normalized) - 1, 1))]
    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        buckets[index] += sign

    norm = math.sqrt(sum(value * value for value in buckets))
    if norm == 0.0:
        return buckets
    return [value / norm for value in buckets]


async def _http_embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    url = settings.EMBEDDING_BASE_URL.rstrip("/") + "/embeddings"
    _assert_allowed(url)

    headers = {"Content-Type": "application/json"}
    if settings.EMBEDDING_API_KEY:
        headers["Authorization"] = f"Bearer {settings.EMBEDDING_API_KEY}"

    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[start : start + EMBED_BATCH_SIZE]
            try:
                response = await client.post(
                    url, headers=headers, json={"model": settings.EMBEDDING_MODEL, "input": batch}
                )
            except httpx.HTTPError as exc:
                raise ApiError(ErrorCode.LLM_UNREACHABLE, "嵌入服务不可达") from exc
            if response.status_code >= 400:
                raise ApiError(ErrorCode.LLM_UNREACHABLE, "嵌入服务返回错误")
            payload = response.json()
            for item in payload.get("data", []):
                vectors.append([float(value) for value in item["embedding"]])
    return vectors


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量嵌入。空输入直接返回空列表，不打网络。"""
    if not texts:
        return []
    settings = get_settings()
    if settings.EMBEDDING_BASE_URL:
        return await _http_embed(texts)
    return [_local_embed(text, settings.EMBEDDING_DIM) for text in texts]


async def embed_query(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """离线嵌入的同步入口，供单元测试与脚本用；配了 HTTP 提供方时不要调用。"""
    settings = get_settings()
    return [_local_embed(text, settings.EMBEDDING_DIM) for text in texts]
