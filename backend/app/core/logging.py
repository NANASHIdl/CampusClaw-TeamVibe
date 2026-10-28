"""结构化日志：一行一条 JSON。

规范依据：docs/specs/05-部署运维规范.md §4 的字段表与「不得落日志」清单。

必填字段：ts / level / module / request_id / event。
request_id 由 core.middleware 绑定到 contextvars，这里通过 merge_contextvars 自动带上，
所以业务代码打日志时不必手动传 request_id。
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import structlog

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def utc_now_iso() -> str:
    """ISO8601，UTC，毫秒精度，带 Z 后缀（PC-10 要求 ts 形如 ...Z）。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _add_ts(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["ts"] = utc_now_iso()
    return event_dict


def configure_logging(level: str = "info", *, console: bool = False) -> None:
    """初始化 structlog。

    默认单行 JSON（05 §4 要求「一行一条 JSON，字段固定」）；
    只有显式要求时才用 console 渲染，供本地肉眼读日志。
    """
    log_level = _LEVELS.get(level.lower(), logging.INFO)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_ts,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.EventRenamer(to="event"),
    ]
    processors.append(
        structlog.dev.ConsoleRenderer()
        if console
        else structlog.processors.JSONRenderer(ensure_ascii=False)
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )


def get_logger(*, module: str) -> Any:
    """取带 module 字段的 logger。module 取值见 05 §4：api / services / repositories / integrations。

    必须用 `structlog.get_logger(module=...)` 而不是 `structlog.get_logger().bind(module=...)`：
    后者会**立刻把 lazy proxy 实体化**，于是任何在 `configure_logging()` 之前 import 的模块
    （core.errors、core.middleware 都在 main 装配前就被 import）会永久停留在 structlog 默认的
    ConsoleRenderer，日志不再是 JSON。传 kwargs 才是延迟绑定，配置生效后才定稿。
    """
    return structlog.get_logger(module=module)
