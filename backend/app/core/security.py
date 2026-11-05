"""口令与会话令牌的密码学原语。

规范依据：
- docs/specs/03-安全开发规范.md §5 §10（bcrypt cost=12、令牌只放 HttpOnly Cookie、库中不存原值）
- openspec/.../specs/identity/spec.md ID-01 / ID-02

只做"怎么算"，不做判断——判断在 services/auth.py。这样本文件可以纯函数测试。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

import bcrypt

# 03 §10：cost=12。写死在这里而不是配置里，避免"某台机器调低一点先跑起来"
BCRYPT_ROUNDS = 12
# bcrypt 的硬上限是 72 字节，超出部分会被静默截断；入参校验在 schemas/ 已限到 72 字符
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """返回 `$2b$12$...`，长度 60。"""
    raw = password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """比对口令。哈希格式非法时返回 False，而不是抛异常把 500 暴露出去。"""
    raw = password.encode("utf-8")[:MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(raw, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    """会话令牌原值。只下发到 Cookie，库中存它的 SHA-256。"""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """令牌的 SHA-256 十六进制串（64 字符）。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def new_join_code(length: int = 8) -> str:
    """入班码：去掉容易看错的 0/O/1/I，只用不易混淆的字符集。"""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
