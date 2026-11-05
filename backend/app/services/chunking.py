"""正文切分。

第 4 课要求：切片是检索的最小单位，命中的是切片而不是整篇材料，且必须能回到原文的
字符区间。因此每个切片除了正文，还要带 `char_start` / `char_end`。

规则（`Settings.CHUNK_SIZE_CHARS` / `CHUNK_OVERLAP_CHARS`，默认 800 / 120）：
1. 优先在段落边界（空行）断开，找不到再退到句末标点，最后才硬切；
2. 相邻切片保留 `overlap` 个字符的重叠，避免答案被切在缝上；
3. 切片序号从 0 连续递增，不允许缺口（MT-07 的判据）。

这是纯函数，不碰数据库与网络，便于单元测试固定输入输出。
"""

from __future__ import annotations

from dataclasses import dataclass

# 段落/句子边界的候选，按优先级排列
_PARAGRAPH_BREAK = "\n\n"
_SENTENCE_BREAKS = ("。", "！", "？", "；", "\n", ".", "!", "?")


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    content: str
    char_start: int
    char_end: int


def _find_break(text: str, start: int, hard_end: int, min_end: int) -> int:
    """在 [min_end, hard_end] 里找一个尽量靠后的自然边界，返回切点（不含）。"""
    window = text[min_end:hard_end]
    position = window.rfind(_PARAGRAPH_BREAK)
    if position != -1:
        return min_end + position + len(_PARAGRAPH_BREAK)

    best = -1
    for mark in _SENTENCE_BREAKS:
        found = window.rfind(mark)
        if found > best:
            best = found
    if best != -1:
        return min_end + best + 1

    return hard_end


def split_text(text: str, size: int = 800, overlap: int = 120) -> list[TextChunk]:
    """把正文切成切片。空正文返回空列表；短正文返回单个切片。"""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be in [0, size)")

    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= size:
        return [TextChunk(index=0, content=normalized, char_start=0, char_end=len(normalized))]

    chunks: list[TextChunk] = []
    start = 0
    total = len(normalized)
    index = 0

    while start < total:
        hard_end = min(start + size, total)
        # 至少切出半个窗口，否则短段落会让切片碎成一句一条
        min_end = min(start + size // 2, total)
        end = hard_end if hard_end >= total else _find_break(normalized, start, hard_end, min_end)
        piece = normalized[start:end]
        if piece.strip():
            chunks.append(TextChunk(index=index, content=piece, char_start=start, char_end=end))
            index += 1

        if end >= total:
            break
        next_start = max(end - overlap, start + 1)
        start = next_start

    return chunks
