"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import setup_metrics
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter
from app.db.redis import pool as redis_pool
from app.db.session import engine

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )
    yield
    await engine.dispose()
    await redis_pool.disconnect()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # --- Rate limiting ---------------------------------------------------
    app.state.limiter = limiter
    # slowapi's handler is typed with the concrete RateLimitExceeded rather than
    # Starlette's broad Exception, which mypy flags; the wiring is correct.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    # --- CORS ------------------------------------------------------------
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # --- Request context / access logs (outermost) ----------------------
    app.add_middleware(RequestContextMiddleware)

    # --- Observability ---------------------------------------------------
    setup_metrics(app)

    # --- Routes ----------------------------------------------------------
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # --- Uploaded images ---------------------------------------------------
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.UPLOAD_DIR),
        name="uploads",
    )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()
