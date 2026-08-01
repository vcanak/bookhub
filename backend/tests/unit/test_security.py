"""Unit tests for password hashing and JWT helpers."""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest
from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_round_trip() -> None:
    password = "S3cretP@ssw0rd"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2")  # bcrypt prefix
    assert verify_password(password, hashed) is True


def test_verify_password_wrong_password_is_false() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("not-the-password", hashed) is False


def test_verify_password_on_garbage_hash_is_false() -> None:
    # A malformed hash must not raise, just return False.
    assert verify_password("anything", "not-a-valid-bcrypt-hash") is False


def test_hash_password_is_salted() -> None:
    # Two hashes of the same password differ thanks to a random salt.
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b


def test_create_and_decode_access_token() -> None:
    token = create_access_token("user-123")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == ACCESS_TOKEN_TYPE
    assert "exp" in payload
    assert "iat" in payload


def test_create_and_decode_refresh_token() -> None:
    token = create_refresh_token("user-456")
    payload = decode_token(token)

    assert payload["sub"] == "user-456"
    assert payload["type"] == REFRESH_TOKEN_TYPE


def test_access_and_refresh_tokens_have_distinct_type_claims() -> None:
    access_payload = decode_token(create_access_token("u"))
    refresh_payload = decode_token(create_refresh_token("u"))

    assert access_payload["type"] == ACCESS_TOKEN_TYPE
    assert refresh_payload["type"] == REFRESH_TOKEN_TYPE
    assert access_payload["type"] != refresh_payload["type"]


def test_subject_is_coerced_to_string() -> None:
    token = create_access_token(789)
    payload = decode_token(token)
    assert payload["sub"] == "789"


def test_expired_token_raises() -> None:
    token = create_access_token("user", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_token_signed_with_wrong_key_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": "attacker", "type": ACCESS_TOKEN_TYPE},
        "a-totally-different-secret-key-32-characters",
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(forged)
