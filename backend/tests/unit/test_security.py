"""口令哈希与 ULID 转换的单元测试。

ID-01 的可观测结果在这里被固定：`password_hash` 以 `$2b$12$` 开头、长度 60、可校验。
`ulid_to_uuid` 是向量点 ID 的唯一来源，改动它会静默打断「切片 ↔ 向量点」的对应关系。
"""

from __future__ import annotations

from uuid import UUID

from app.core.ids import is_valid_ulid, new_ulid, ulid_to_uuid
from app.core.security import hash_password, hash_session_token, verify_password


def test_password_hash_format_and_verification() -> None:
    digest = hash_password("correct-horse-battery")

    assert digest.startswith("$2b$12$")
    assert len(digest) == 60
    assert verify_password("correct-horse-battery", digest) is True
    assert verify_password("wrong-password", digest) is False


def test_verify_password_tolerates_broken_hash() -> None:
    # 哈希格式非法时返回 False，不能抛异常把 500 暴露给调用方
    assert verify_password("whatever", "not-a-bcrypt-hash") is False


def test_same_password_gets_different_salt() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_session_token_hash_is_stable_and_not_reversible() -> None:
    token = "some-session-token-value"

    assert hash_session_token(token) == hash_session_token(token)
    assert len(hash_session_token(token)) == 64
    assert token not in hash_session_token(token)


def test_ulid_to_uuid_is_bijective_for_any_ulid() -> None:
    for _ in range(50):
        ulid = new_ulid()
        uuid_text = ulid_to_uuid(ulid)
        # 同一个 128 位值的 UUID 写法：可解析、长度固定
        assert str(UUID(uuid_text)) == uuid_text


def test_ulid_generator_is_valid() -> None:
    assert is_valid_ulid(new_ulid())
