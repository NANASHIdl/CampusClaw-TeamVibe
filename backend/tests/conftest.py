"""测试公共装配。

必须在 import `app.*` 之前把必填配置写进 os.environ：`app/main.py` 在模块级调用
`load_settings()`，缺键会 SystemExit(1)，测试进程会直接死掉。

配置值全部是假的，不含任何真实密钥（AGENTS.md §1.3）。
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

# ---- 测试环境配置：先于任何 app 导入 ----
os.environ.update(
    {
        "APP_ENV": "test",
        "APP_VERSION": "0.0.1-test",
        "APP_COMMIT": "testcommit",
        "WEB_PORT": "8080",
        "LOG_LEVEL": "warn",
        "SESSION_SECRET": "t" * 40,
        "DATABASE_URL": "postgresql+asyncpg://test:test@127.0.0.1:5432/test",
        "QDRANT_URL": "http://127.0.0.1:6333",
        "LLM_BASE_URL": "http://127.0.0.1:9999",
        "LLM_API_KEY": "test-key-not-a-real-secret",
        "LLM_MODEL": "test-model-v1",
        "EMBEDDING_MODEL": "test-embed-v1",
    }
)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """进程内调用应用，不起真实端口。"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
