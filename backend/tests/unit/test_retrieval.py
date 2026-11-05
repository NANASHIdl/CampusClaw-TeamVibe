"""检索纯逻辑的单元测试：切词、摘要窗口、RRF 融合。

这些函数不碰数据库与网络，所以可以在任何机器上直接跑；
接口级的三条判据用 curl 复现，见 docs/changes/2026-11-05-lesson3-4-implementation.md。
"""

from __future__ import annotations

from app.services.retrieval import Hit, _fuse, build_grams, make_snippet


def _hit(material_id: str, chunk_index: int, score: float = 1.0) -> Hit:
    return Hit(
        material_id=material_id,
        chunk_index=chunk_index,
        title="测试材料",
        snippet="片段",
        score=score,
        char_start=0,
        char_end=10,
    )


def test_build_grams_splits_chinese_into_bigrams() -> None:
    grams = build_grams("递归树")

    assert "递归" in grams
    assert "归树" in grams
    # 整串排在最前，用于子串优先匹配
    assert grams[0] == "递归树"


def test_build_grams_ignores_whitespace_and_caps_length() -> None:
    grams = build_grams("主 定理 怎么 用 递归树 证明一下")

    assert all(" " not in gram for gram in grams)
    assert len(grams) <= 8


def test_snippet_centers_on_keyword() -> None:
    content = "前" * 300 + "递归树" + "后" * 300
    snippet = make_snippet(content, "递归树", width=120)

    assert "递归树" in snippet
    assert len(snippet) <= 121  # 含末尾省略号


def test_snippet_falls_back_to_head_when_no_match() -> None:
    snippet = make_snippet("毫无关系的一段正文", "递归树", width=10)

    assert snippet.startswith("毫无关系")


def test_fuse_prefers_items_ranked_high_by_both_paths() -> None:
    keyword = [_hit("A", 0), _hit("A", 1)]
    vector = [_hit("A", 1), _hit("B", 0)]

    fused = _fuse(keyword, vector, limit=8)

    # (A,1) 在两路里都靠前，应排第一
    assert fused[0].material_id == "A"
    assert fused[0].chunk_index == 1
    # 归一化后最高分为 1.0，全部落在 0–1
    assert fused[0].score == 1.0
    assert all(0.0 <= hit.score <= 1.0 for hit in fused)


def test_fuse_respects_limit_and_stable_order() -> None:
    keyword = [_hit("A", index) for index in range(10)]

    fused = _fuse(keyword, [], limit=3)

    assert len(fused) == 3
    assert [hit.chunk_index for hit in fused] == [0, 1, 2]


def test_fuse_empty_inputs() -> None:
    assert _fuse([], [], limit=8) == []
