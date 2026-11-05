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
    """三项依赖各带 2 秒超时，并发探测；任一项失败不影响其他项的结果。

    `llm` 是有条件依赖：本项目的检索链路支持**离线确定性嵌入**
    （`EMBEDDING_BASE_URL` 为空即启用，见 04 §检索选型）。这种部署下根本没有
    外部模型服务，若仍去探它，`/health/ready` 会永远 503、`api` 容器永远 unhealthy，
    于是「不用模型」反而变成起不来的原因。因此未配置模型地址时该项报 `up`：
    语义是「当前配置下这项不构成依赖」，而不是「探测通过」。
    deps 的取值集合仍只有 up/down，与 05 §3 一致。
    """
    settings = get_settings()

    db_ok, qdrant_ok = await asyncio.gather(
        ping_db(),
        probe_qdrant(settings.QDRANT_URL),
    )

    if settings.EMBEDDING_BASE_URL.strip():
        llm_ok = await probe_llm(settings.LLM_BASE_URL)
    else:
        llm_ok = True

    return {
        "db": "up" if db_ok else "down",
        "qdrant": "up" if qdrant_ok else "down",
        "llm": "up" if llm_ok else "down",
    }


def all_up(deps: dict[str, str]) -> bool:
    return all(deps.get(key) == "up" for key in DEP_KEYS)
