"""Guard the slowapi usage pattern used by the auth endpoints.

slowapi's ``headers_enabled=True`` makes a ``@limiter.limit`` decorated route
call ``_inject_headers``, which requires the endpoint to declare a
``response: Response`` parameter. Omitting it raises a 500 on the success path
*only when rate limiting is enabled* — which the rest of the suite disables.
This hermetic test (in-memory storage, no Redis) locks in the correct pattern.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

pytestmark = pytest.mark.unit


def _build_app() -> FastAPI:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
        headers_enabled=True,
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/ping")
    @limiter.limit("2/minute")
    async def ping(request: Request, response: Response) -> dict[str, bool]:
        # Returns a dict (not a Response) — the `response` param is what lets
        # slowapi inject rate-limit headers without raising.
        return {"ok": True}

    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def test_decorated_route_succeeds_and_injects_headers() -> None:
    async with _client(_build_app()) as client:
        first = await client.get("/ping")
        assert first.status_code == 200
        assert first.json() == {"ok": True}
        # Header injection working proves the `response` parameter is wired up.
        assert "x-ratelimit-limit" in {k.lower() for k in first.headers}


async def test_limit_is_enforced() -> None:
    async with _client(_build_app()) as client:
        assert (await client.get("/ping")).status_code == 200
        assert (await client.get("/ping")).status_code == 200
        # Third request within the window exceeds "2/minute".
        assert (await client.get("/ping")).status_code == 429
