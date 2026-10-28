"""配置外置：只从环境变量读，必填键缺失即启动失败。

规范依据：
- docs/specs/02-后端开发规范.md §7（必填键的**唯一权威清单**，共 8 个 + SEED_* 条件必填）
- specs/platform-core/spec.md 的 PC-01 / PC-02 / PC-03

任何地方出现第二份必填键清单即为缺陷（02 §7 原话）。
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import utc_now_iso

# 02 §7 的权威清单：键名与约束一一对应，改动必须同步该表
REQUIRED_KEYS: tuple[str, ...] = (
    "SESSION_SECRET",
    "DATABASE_URL",
    "QDRANT_URL",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "WEB_PORT",
)

# 仅 dev / test 必填；APP_ENV=prod 时存在即启动失败
SEED_KEYS: tuple[str, ...] = (
    "SEED_TEACHER_EMAIL",
    "SEED_TEACHER_PASSWORD",
    "SEED_STUDENT_EMAIL",
    "SEED_STUDENT_PASSWORD",
)


def _fatal(event: str, keys: list[str], reason: str | None = None) -> None:
    """启动失败时打一行 JSON 到 stderr 并退出。

    此时日志系统还没装配完，所以直接用 json.dumps 写 stderr，
    保证 PC-02 / PC-03 要求的那行 JSON 一定出现。
    """
    payload: dict[str, object] = {
        "ts": utc_now_iso(),
        "level": "error",
        "module": "config",
        "event": event,
        "keys": keys,
    }
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)


class Settings(BaseSettings):
    """全部配置项。必填项无默认值，缺失时 pydantic 直接报错。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- 应用 ----
    APP_ENV: Literal["dev", "test", "prod"] = "dev"
    APP_VERSION: str = "0.0.1"
    APP_COMMIT: str = "dev"
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    WEB_PORT: int = Field(ge=1, le=65535)
    LOG_LEVEL: str = "info"
    # 默认一律单行 JSON（05 §4）。只在本地想肉眼读日志时显式设成 console，
    # 不能让「开发环境」自动变成非 JSON——那会让 PC-10 的 json.loads 断言默认就不成立。
    LOG_FORMAT: Literal["json", "console"] = "json"

    # ---- 数据库 ----
    DATABASE_URL: str = Field(min_length=1)

    # ---- 向量库 ----
    QDRANT_URL: str = Field(min_length=1)
    QDRANT_COLLECTION: str = "materials"

    # ---- 会话 ----
    SESSION_SECRET: str = Field(min_length=32)
    SESSION_TTL_MINUTES: int = Field(default=720, ge=1)

    # ---- 模型与嵌入 ----
    LLM_BASE_URL: str = Field(min_length=1)
    LLM_API_KEY: str = Field(min_length=1)
    LLM_MODEL: str = Field(min_length=1)
    LLM_TIMEOUT_SECONDS: int = Field(default=20, ge=1)
    LLM_MAX_RETRIES: int = Field(default=1, ge=0)
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = Field(min_length=1)

    # ---- 检索 ----
    SEARCH_VECTOR_MIN: float = Field(default=0.35, ge=0.0, le=1.0)
    SEARCH_TOP_K: int = Field(default=8, ge=1, le=50)

    # ---- 上传与切片 ----
    UPLOAD_MAX_BYTES: int = Field(default=20 * 1024 * 1024, ge=1)
    UPLOAD_MAX_FILES: int = Field(default=20, ge=1)
    UPLOAD_ALLOWED_EXT: str = "pdf,md,txt,docx"
    CHUNK_SIZE_CHARS: int = Field(default=800, ge=1)
    CHUNK_OVERLAP_CHARS: int = Field(default=120, ge=0)

    # ---- 出站白名单 ----
    ALLOWED_OUTBOUND_HOSTS: str = ""

    # ---- 预置账号（仅 dev / test）----
    SEED_TEACHER_EMAIL: str = ""
    SEED_TEACHER_PASSWORD: str = ""
    SEED_STUDENT_EMAIL: str = ""
    SEED_STUDENT_PASSWORD: str = ""

    @property
    def allowed_outbound_hosts(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_OUTBOUND_HOSTS.split(",") if h.strip()]

    @property
    def allowed_extensions(self) -> list[str]:
        return [e.strip().lower() for e in self.UPLOAD_ALLOWED_EXT.split(",") if e.strip()]

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV in {"dev", "test"}


def load_settings() -> Settings:
    """读配置；缺失或非法即 SystemExit(1)，不带着默认值继续跑。"""
    try:
        settings = Settings()
    except ValidationError as exc:
        missing: list[str] = []
        invalid: list[str] = []
        reason: str | None = None

        for err in exc.errors():
            field = ".".join(str(part) for part in err["loc"])
            if err["type"] == "missing":
                missing.append(field)
            else:
                invalid.append(field)
                if err["type"] == "string_too_short" and field == "SESSION_SECRET":
                    reason = "min_length_32"

        if missing:
            _fatal("missing_env", sorted(missing))
            raise SystemExit(1) from None

        _fatal("invalid_env", sorted(invalid), reason or "invalid_value")
        raise SystemExit(1) from None

    # 生产环境出现预置账号 = 事故，直接拒绝启动（02 §7）
    if settings.APP_ENV == "prod":
        leaked = [key for key in SEED_KEYS if getattr(settings, key)]
        if leaked:
            _fatal("invalid_env", leaked, "seed_in_prod")
            raise SystemExit(1)

    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """进程内单例。测试用 get_settings.cache_clear() 重置。"""
    return load_settings()
