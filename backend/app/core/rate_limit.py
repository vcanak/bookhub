"""Redis-backed rate limiting via slowapi."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _client_key(request) -> str:  # type: ignore[no-untyped-def]
    """Rate-limit key: authenticated user id when available, else client IP."""
    user = getattr(request.state, "user_id", None)
    if user:
        return str(user)
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_key,
    storage_uri=settings.rate_limit_storage_uri,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)
