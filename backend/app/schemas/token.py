"""Authentication token schemas."""

from __future__ import annotations

from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2-style token pair returned on login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type label, not a secret


class TokenPayload(BaseModel):
    """Decoded JWT claims."""

    sub: str | None = None
    exp: int | None = None
    iat: int | None = None
    type: str | None = None


class RefreshRequest(BaseModel):
    """Body for the token refresh endpoint."""

    refresh_token: str
