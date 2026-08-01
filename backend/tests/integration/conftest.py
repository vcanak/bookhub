"""Fixtures for integration tests (require a reachable PostgreSQL and Redis).

The environment is already configured by the root ``tests/conftest.py`` which
imports before any ``app`` module, so it is safe to import app modules here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

# Importing the models package ensures every table is registered on
# ``Base.metadata`` before ``create_all`` runs.
import app.models  # noqa: F401
import httpx
import pytest
from app import crud
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.main import app as fastapi_app
from app.models.user import User
from app.schemas.user import UserCreate
from asgi_lifespan import LifespanManager
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Schema lifecycle
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
async def _create_test_schema() -> AsyncIterator[None]:
    """Create all tables once for the session, drop them at the end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture(autouse=True)
async def _truncate_tables() -> AsyncIterator[None]:
    """Truncate every table between tests to guarantee isolation."""
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.exec_driver_sql(
                f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'
            )


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session bound to the application engine."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client that drives the ASGI app with a managed lifespan."""
    async with LifespanManager(fastapi_app):
        transport = httpx.ASGITransport(app=fastapi_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# User / auth fixtures
# ---------------------------------------------------------------------------
async def _create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str = "ChangeMe123!",
    full_name: str | None = None,
    is_superuser: bool = False,
) -> User:
    """Create (and persist) a user via the real CRUD layer."""
    user = await crud.user.create(
        db,
        obj_in=UserCreate(email=email, password=password, full_name=full_name),
    )
    if is_superuser:
        user.is_superuser = True
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@pytest.fixture
def create_user(db_session: AsyncSession):
    """Factory fixture returning a coroutine that creates users on demand."""

    async def _factory(
        *,
        email: str,
        password: str = "ChangeMe123!",
        full_name: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        return await _create_user(
            db_session,
            email=email,
            password=password,
            full_name=full_name,
            is_superuser=is_superuser,
        )

    return _factory


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def normal_user(db_session: AsyncSession) -> User:
    return await _create_user(
        db_session,
        email="user@example.com",
        password="UserPass123!",
        full_name="Normal User",
    )


@pytest.fixture
def normal_user_token_headers(normal_user: User) -> dict[str, str]:
    return _auth_headers(normal_user)


@pytest.fixture
async def superuser(db_session: AsyncSession) -> User:
    return await _create_user(
        db_session,
        email="admin@example.com",
        password="AdminPass123!",
        full_name="Super User",
        is_superuser=True,
    )


@pytest.fixture
def superuser_token_headers(superuser: User) -> dict[str, str]:
    return _auth_headers(superuser)
