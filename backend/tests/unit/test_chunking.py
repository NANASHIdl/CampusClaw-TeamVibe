"""切分的单元测试。

覆盖的可观测结果：
- 切片序号从 0 连续，无缺口（MT-07 的判据）；
- `char_start`/`char_end` 指回原文区间，`text[char_start:char_end] == content`；
- 相邻切片保留重叠，答案不会被切在缝上；
- 段落边界优先于硬切。
"""

from __future__ import annotations

import itertools

from app.services.chunking import split_text

PARAGRAPH = "第一段讲主定理的递归树证明。" * 10
SECOND = "第二段讲平衡树的分裂情况。" * 10


def test_short_text_is_single_chunk() -> None:
    chunks = split_text("很短的一段话。", size=800, overlap=120)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == len("很短的一段话。")


def test_empty_text_returns_no_chunk() -> None:
    assert split_text("   \n\n  ") == []


def test_indices_are_contiguous_and_offsets_round_trip() -> None:
    text = (PARAGRAPH + "\n\n" + SECOND) * 6
    chunks = split_text(text, size=800, overlap=120)

    assert len(chunks) > 1
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    for chunk in chunks:
        assert text[chunk.char_start : chunk.char_end] == chunk.content


def test_chunk_sizes_respect_limit() -> None:
    text = "无空行的连续正文。" * 500
    chunks = split_text(text, size=800, overlap=120)

    assert all(len(chunk.content) <= 800 for chunk in chunks)


def test_adjacent_chunks_overlap() -> None:
    text = "".join(f"第{index}句。" for index in range(400))
    chunks = split_text(text, size=800, overlap=120)

    for previous, current in itertools.pairwise(chunks):
        # 上一片的结尾与下一片的开头必须有 120 字符的重叠
        assert current.char_start == previous.char_end - 120
        assert previous.content[-120:] == current.content[:120]


def test_prefers_paragraph_boundary() -> None:
    text = "甲" * 700 + "\n\n" + "乙" * 700
    chunks = split_text(text, size=800, overlap=120)

    # 第一片应在段落分隔处收尾（保留空行，char 区间才对得上原文），
    # 而不是把两个段落各切一半
    assert chunks[0].char_end >= 700
    assert chunks[0].content.rstrip().endswith("甲")
