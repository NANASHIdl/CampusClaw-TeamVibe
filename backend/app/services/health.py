"""健康检查业务：并发探测依赖并汇总状态。

规范依据：
- docs/specs/05-部署运维规范.md §3（三个端点语义、任一 down 即 503、进程不退出）
- specs/platform-core/spec.md 的 PC-12 / PC-13

本层不 import fastapi（02 §1 判据）：返回纯数据结构，由 api/ 组装响应。
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.integrations.probes import probe_llm, probe_qdrant
from app.repositories.base import ping_db

DEP_KEYS = ("db", "qdrant", "llm")


async def collect_deps() -> dict[str, str]:
    """三项依赖各带 2 秒超时，并发探测；任一项失败不影响其他项的结果。"""
    settings = get_settings()

    db_ok, qdrant_ok, llm_ok = await asyncio.gather(
        ping_db(),
        probe_qdrant(settings.QDRANT_URL),
        probe_llm(settings.LLM_BASE_URL),
    )

    return {
        "db": "up" if db_ok else "down",
        "qdrant": "up" if qdrant_ok else "down",
        "llm": "up" if llm_ok else "down",
    }


def all_up(deps: dict[str, str]) -> bool:
    return all(deps.get(key) == "up" for key in DEP_KEYS)
