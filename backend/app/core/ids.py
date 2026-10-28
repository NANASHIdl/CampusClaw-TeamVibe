"""ULID 生成与校验。

26 位 Crockford Base32：前 10 位是 48 位毫秒时间戳，后 16 位是 80 位随机数。
时间戳在前使 ULID 可按创建顺序排序，适合做数据库主键与 request_id。

不引入第三方依赖：实现只有 30 行，加依赖的成本高于收益（见 AGENTS.md §6.3）。
"""

from __future__ import annotations

import os
import time

# Crockford Base32：去掉 I / L / O / U，避免与 1 / 0 混淆
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ALPHABET_SET = frozenset(_ALPHABET)
_ULID_LENGTH = 26
_TIME_MASK = (1 << 48) - 1


def new_ulid() -> str:
    """生成一个新的 26 位大写 ULID。"""
    timestamp = int(time.time() * 1000) & _TIME_MASK
    randomness = int.from_bytes(os.urandom(10), "big")
    value = (timestamp << 80) | randomness

    chars: list[str] = []
    for _ in range(_ULID_LENGTH):
        chars.append(_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def is_valid_ulid(value: str | None) -> bool:
    """校验是否为合法的 26 位 ULID；用于判断请求头里的 X-Request-ID 能否继承。"""
    return (
        isinstance(value, str)
        and len(value) == _ULID_LENGTH
        and all(char in _ALPHABET_SET for char in value)
    )


def ulid_to_timestamp_ms(value: str) -> int:
    """从 ULID 解出毫秒时间戳；格式非法时抛 ValueError。"""
    if not is_valid_ulid(value):
        raise ValueError(f"not a ulid: {value!r}")

    timestamp = 0
    for char in value[:10]:
        timestamp = (timestamp << 5) | _ALPHABET.index(char)
    return timestamp
