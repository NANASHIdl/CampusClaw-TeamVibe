#!/usr/bin/env python3
"""第 3、4 课验收判据的可复现脚本。

用法（先在仓库根目录 `docker compose up --build -d`，等 health 变绿）：

    backend/.venv/Scripts/python.exe scripts/verify_lesson34.py
    # 停掉向量库后再跑一次降级判据：
    docker compose stop qdrant
    backend/.venv/Scripts/python.exe scripts/verify_lesson34.py --expect-qdrant-down

只依赖 httpx（已在 backend/requirements.lock 里），不需要额外安装。
凭据从 .env 读，可用环境变量覆盖。

退出码：全部通过 0，任一判据不通过 1。
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
ENV = dotenv_values(ROOT / ".env") if (ROOT / ".env").is_file() else {}

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or str(ENV.get(name) or default)


def sample_ulid() -> str:
    """造一个格式合法但不存在的 ULID，用于「不存在」的对照请求。"""
    payload = "".join(secrets.choice(ALPHABET) for _ in range(26))
    ts = "".join(secrets.choice(ALPHABET) for _ in range(10))
    return ts + payload[10:]


class Checker:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append((name, ok, detail))
        if not ok:
            self.failures.append(name)
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}{(' — ' + detail) if detail else ''}")
        return ok

    def summary(self) -> int:
        print()
        total = len(self.results)
        passed = total - len(self.failures)
        print(f"合计 {passed}/{total} 项通过")
        if self.failures:
            print("未通过：" + "、".join(self.failures))
            return 1
        return 0


def make_client() -> httpx.Client:
    return httpx.Client(base_url=env("BASE_URL", f"http://localhost:{env('WEB_PORT', '8080')}"), timeout=20)


def login(client: httpx.Client, email: str, password: str) -> bool:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    return response.status_code == 200 and body.get("code") == 0


def strip_request_id(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key != "request_id"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-qdrant-down", action="store_true", help="向量库已停止时验证降级")
    args = parser.parse_args()

    teacher_email = env("SEED_TEACHER_EMAIL")
    teacher_password = env("SEED_TEACHER_PASSWORD")
    student_email = env("SEED_STUDENT_EMAIL")
    student_password = env("SEED_STUDENT_PASSWORD")
    suffix = env("SEED_CLASS_B_SUFFIX", "+b")

    student_b_email = student_email.replace("@", f"{suffix}@", 1)

    checker = Checker()

    anonymous = make_client()
    student = make_client()
    student_b = make_client()
    teacher = make_client()

    print("准备：登录三个账号")
    if not checker.check("教师登录", login(teacher, teacher_email, teacher_password)):
        return checker.summary()
    if not checker.check("A 班学生登录", login(student, student_email, student_password)):
        return checker.summary()
    checker.check("B 班学生登录", login(student_b, student_b_email, student_password))

    # ---------- 第 3 课判据一：未认证拿不到任何材料内容 ----------
    print("\n第 3 课 · 判据一：未认证拿不到材料内容")
    response = anonymous.get("/api/v1/materials")
    payload = response.json()
    checker.check("未携带会话返回 401", response.status_code == 401, f"实际 {response.status_code}")
    checker.check("错误码为 1101", payload.get("code") == 1101, f"实际 {payload.get('code')}")
    checker.check("响应体不含资料标题", "title" not in response.text and "items" not in response.text)

    # ---------- 第 3 课判据二：跨班与不存在不可区分 ----------
    print("\n第 3 课 · 判据二：跨班与不存在不可区分")
    b_page = student_b.get("/api/v1/materials", params={"page": 1, "page_size": 20}).json()
    b_items = b_page.get("data", {}).get("items", [])
    if checker.check("B 班有可对照的资料", len(b_items) > 0, f"实际 {len(b_items)} 条"):
        b_material_id = b_items[0]["id"]
        cross = student.get(f"/api/v1/materials/{b_material_id}")
        missing = student.get(f"/api/v1/materials/{sample_ulid()}")
        checker.check("A 班读 B 班资料返回 404", cross.status_code == 404, f"实际 {cross.status_code}")
        checker.check("不存在也返回 404", missing.status_code == 404, f"实际 {missing.status_code}")
        same = strip_request_id(cross.json()) == strip_request_id(missing.json())
        checker.check("两者响应体除 request_id 外完全一致", same)
        checker.check("响应中不含 B 班资料标题", b_items[0]["title"] not in cross.text)

        cross_file = student.get(f"/api/v1/materials/{b_material_id}/file")
        checker.check("跨班下载原文同样 404", cross_file.status_code == 404, f"实际 {cross_file.status_code}")

    # ---------- 第 3 课判据三：越权上传不留痕迹 ----------
    print("\n第 3 课 · 判据三：越权上传被拒且不留痕迹")
    before = student.get("/api/v1/materials", params={"page": 1, "page_size": 1}).json()
    before_total = before.get("data", {}).get("total")
    response = student.post(
        "/api/v1/materials",
        files={"files": ("intruder.md", "# 学生不该能上传\n\n这段不该入库。", "text/markdown")},
    )
    payload = response.json()
    checker.check("学生上传返回 404", response.status_code == 404, f"实际 {response.status_code}")
    checker.check("错误码为 1202", payload.get("code") == 1202, f"实际 {payload.get('code')}")
    after = student.get("/api/v1/materials", params={"page": 1, "page_size": 1}).json()
    checker.check(
        "资料条数未变化",
        before_total == after.get("data", {}).get("total"),
        f"{before_total} → {after.get('data', {}).get('total')}",
    )

    # ---------- 第 4 课判据一：三条路径可区分 ----------
    print("\n第 4 课 · 判据一：三条检索路径可区分")
    keyword = student.get("/api/v1/search", params={"q": "递归树", "mode": "keyword"})
    keyword_body = keyword.json()
    keyword_hits = keyword_body.get("data", {}).get("hits", [])
    checker.check("关键词模式 200", keyword.status_code == 200, f"实际 {keyword.status_code}")
    checker.check("关键词模式有命中（不依赖模型与向量库）", len(keyword_hits) > 0, f"{len(keyword_hits)} 条")

    vector = student.get("/api/v1/search", params={"q": "主定理怎么用递归树证明", "mode": "vector"})
    hybrid = student.get("/api/v1/search", params={"q": "主定理怎么用递归树证明", "mode": "hybrid"})
    checker.check("向量模式返回 200 或 503（不出现 5xx 其它码）", vector.status_code in (200, 503), f"实际 {vector.status_code}")
    if args.expect_qdrant_down:
        # 降级模式下混合模式必然 503，200 这条判据不适用（具体降级判据在下面单独验）
        print(f"  [SKIP] 混合模式返回 200 — 向量库已按预期停止")
    else:
        checker.check("混合模式返回 200", hybrid.status_code == 200, f"实际 {hybrid.status_code}")

    bad_mode = student.get("/api/v1/search", params={"q": "递归树", "mode": "semantic"})
    checker.check(
        "非法模式返回 400 且 code=1003",
        bad_mode.status_code == 400 and bad_mode.json().get("code") == 1003,
        f"实际 {bad_mode.status_code}/{bad_mode.json().get('code')}",
    )

    if args.expect_qdrant_down:
        degraded = student.get("/api/v1/search", params={"q": "递归树", "mode": "hybrid"})
        checker.check("向量库停机后混合模式 503", degraded.status_code == 503, f"实际 {degraded.status_code}")
        checker.check("降级错误码为 1502", degraded.json().get("code") == 1502, f"实际 {degraded.json().get('code')}")
        checker.check("提示改为关键词模式", "关键词" in degraded.json().get("message", ""))
        still = student.get("/api/v1/search", params={"q": "递归树", "mode": "keyword"})
        checker.check("关键词模式仍可用", still.status_code == 200 and bool(still.json().get("data", {}).get("hits")))

    # ---------- 第 4 课判据二：班级边界不随请求改变 ----------
    print("\n第 4 课 · 判据二：班级边界不随请求改变")
    b_class_id = (student_b.get("/api/v1/me").json().get("data") or {}).get("class_id") or ""
    only_in_b = "摊还分析"
    without_param = student.get("/api/v1/search", params={"q": only_in_b, "mode": "keyword"}).json()
    with_param = student.get(
        "/api/v1/search",
        params={"q": only_in_b, "mode": "keyword", "class_id": b_class_id},
    ).json()
    hits_without = without_param.get("data", {}).get("hits", [])
    checker.check("A 班检索只出现在 B 班的词：无命中或仅 A 班内容", all(
        hit["material_id"] not in {item["id"] for item in b_items} for hit in hits_without
    ) if hits_without else True, f"{len(hits_without)} 条")
    checker.check(
        "伪造 class_id 参数不改变结果",
        [hit["material_id"] for hit in hits_without]
        == [hit["material_id"] for hit in with_param.get("data", {}).get("hits", [])],
    )

    # ---------- 第 4 课判据三：无依据不生成，出处可回溯 ----------
    print("\n第 4 课 · 判据三：无依据时明确返回未找到")
    # 降级模式下没有向量库，混合模式会直接 503；「无依据」这条判据用关键词模式同样成立，
    # 因为它考的是「查不到就明说」，与走哪条路无关。
    no_hit_mode = "keyword" if args.expect_qdrant_down else "hybrid"
    no_hit = student.get("/api/v1/search", params={"q": "今天天气怎么样", "mode": no_hit_mode}).json()
    data = no_hit.get("data") or {}
    checker.check("无命中时 hits 为空", data.get("hits") == [], f"{len(data.get('hits') or [])} 条")
    checker.check("文案为固定文案", data.get("message") == "资料中未找到相关内容", str(data.get("message")))

    if keyword_hits:
        first = keyword_hits[0]
        checker.check(
            "命中带材料标题、切片序号与字符区间",
            bool(first.get("title")) and isinstance(first.get("chunk_index"), int) and first.get("char_end", 0) > first.get("char_start", 0),
        )
        detail = student.get(f"/api/v1/materials/{first['material_id']}")
        checker.check("出处可打开资料详情", detail.status_code == 200, f"实际 {detail.status_code}")

    # ---------- 入参与未认证 ----------
    print("\n补充：入参校验与未认证")
    too_long = student.get("/api/v1/search", params={"q": "问" * 201, "mode": "keyword"})
    checker.check("超长查询 400 code=1001", too_long.status_code == 400 and too_long.json().get("code") == 1001)
    unauth_search = anonymous.get("/api/v1/search", params={"q": "递归树"})
    checker.check("未登录检索 401", unauth_search.status_code == 401, f"实际 {unauth_search.status_code}")

    return checker.summary()


if __name__ == "__main__":
    sys.exit(main())
