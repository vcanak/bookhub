"""Async Redis client and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

pool: ConnectionPool = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


def get_redis_client() -> Redis:
    """Return a Redis client bound to the shared connection pool."""
    return Redis(connection_pool=pool)


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency yielding a Redis client."""
    client = get_redis_client()
    try:
        yield client
    finally:
        # aclose() is the correct async close for redis-py 5.x (close() is
        # deprecated); the bundled type stubs do not yet declare it.
        await client.aclose()  # type: ignore[attr-defined]
