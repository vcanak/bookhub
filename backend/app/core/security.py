"""Password hashing and JWT token utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - JWT claim value, not a secret
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105 - JWT claim value, not a secret

# bcrypt silently truncates inputs longer than 72 bytes; we hash a SHA-style
# pre-digest? No — instead we enforce the documented limit at the schema layer
# (password max_length=128) and rely on bcrypt's standard behaviour here.


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str | Any,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    expire = now + expires_delta
    claims: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": token_type,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token."""
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token."""
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising ``jwt.PyJWTError`` on failure."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
