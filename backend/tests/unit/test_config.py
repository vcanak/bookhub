"""Unit tests for application settings."""

from __future__ import annotations

import pytest
from app.core.config import Settings, settings

pytestmark = pytest.mark.unit

# The sentinel insecure secret embedded in app.core.config. The production
# guard refuses to start while this value is in place.
_INSECURE_SECRET = "CHANGE_ME_insecure_dev_secret_key_minimum_32_chars_long"


def test_settings_loads_in_test_environment() -> None:
    assert settings.ENVIRONMENT == "test"
    assert settings.is_production is False
    # SECRET_KEY came from the conftest bootstrap and meets the length floor.
    assert len(settings.SECRET_KEY) >= 32


def test_sqlalchemy_database_uri_uses_asyncpg() -> None:
    uri = settings.SQLALCHEMY_DATABASE_URI
    assert uri.startswith("postgresql+asyncpg://")
    assert settings.POSTGRES_DB in uri
    assert str(settings.POSTGRES_PORT) in uri


def test_sqlalchemy_sync_uri_uses_psycopg() -> None:
    assert settings.SQLALCHEMY_DATABASE_URI_SYNC.startswith("postgresql+psycopg://")


def test_redis_url_format_without_password() -> None:
    expected = (
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
    assert settings.REDIS_URL == expected


def test_redis_url_includes_password_when_set() -> None:
    s = Settings(
        SECRET_KEY="x" * 32,
        REDIS_HOST="cache",
        REDIS_PORT=6380,
        REDIS_DB=2,
        REDIS_PASSWORD="hunter2",
    )
    assert s.REDIS_URL == "redis://:hunter2@cache:6380/2"


def test_celery_urls_fall_back_to_redis_url() -> None:
    s = Settings(SECRET_KEY="x" * 32)
    assert s.celery_broker_url == s.REDIS_URL
    assert s.celery_result_backend == s.REDIS_URL


def test_celery_urls_use_explicit_values_when_provided() -> None:
    s = Settings(
        SECRET_KEY="x" * 32,
        CELERY_BROKER_URL="redis://broker:6379/3",
        CELERY_RESULT_BACKEND="redis://backend:6379/4",
    )
    assert s.celery_broker_url == "redis://broker:6379/3"
    assert s.celery_result_backend == "redis://backend:6379/4"


def test_cors_origins_parsed_from_comma_string() -> None:
    s = Settings(
        SECRET_KEY="x" * 32,
        BACKEND_CORS_ORIGINS="https://a.example, https://b.example",
    )
    assert s.BACKEND_CORS_ORIGINS == [
        "https://a.example",
        "https://b.example",
    ]


def test_production_guard_rejects_insecure_secret() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(ENVIRONMENT="production", SECRET_KEY=_INSECURE_SECRET)


def test_production_guard_allows_strong_secret() -> None:
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-properly-strong-production-secret-key-value",
    )
    assert s.is_production is True
