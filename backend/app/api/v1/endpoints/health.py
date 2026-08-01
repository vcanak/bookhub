"""Health and readiness endpoints for orchestrators and load balancers."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DBSession, RedisClient
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.common import HealthCheck

router = APIRouter()


@router.get("", response_model=HealthCheck, summary="Basic health check")
@limiter.exempt
async def health() -> HealthCheck:
    return HealthCheck(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/live", summary="Liveness probe")
@limiter.exempt
async def liveness() -> dict[str, str]:
    """Cheap check: the process is up and serving requests."""
    return {"status": "alive"}


@router.get("/ready", response_model=HealthCheck, summary="Readiness probe")
@limiter.exempt
async def readiness(
    db: DBSession,
    redis: RedisClient,
    response: Response,
) -> HealthCheck:
    """Verify downstream dependencies (database + cache) are reachable."""
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheck(
        status="ok" if healthy else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        checks=checks,
    )
