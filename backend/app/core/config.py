"""Application configuration.

All settings are loaded from environment variables (and an optional ``.env``
file) using ``pydantic-settings``. A single cached :data:`settings` instance is
exposed for import throughout the application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    Field,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel default used in non-production environments so the app runs out of
# the box. A guard below refuses to start in production while this is in place.
_INSECURE_SECRET = "CHANGE_ME_insecure_dev_secret_key_minimum_32_chars_long"  # noqa: S105 - intentional dev-only sentinel; production guard rejects it


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    PROJECT_NAME: str = "FastAPI Starter"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Production-grade FastAPI starter."
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["local", "development", "staging", "production", "test"] = (
        "local"
    )
    DEBUG: bool = False

    # --- Logging ---------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Security / JWT --------------------------------------------------
    SECRET_KEY: str = Field(default=_INSECURE_SECRET, min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Uploads ----------------------------------------------------------
    # ponytail: local-disk image storage; swap for S3/Cloudinary when the app
    # outgrows a single host.
    UPLOAD_DIR: Path = Path("uploads")

    # --- CORS ------------------------------------------------------------
    BACKEND_CORS_ORIGINS: list[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _assemble_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # --- Database --------------------------------------------------------
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"  # noqa: S105 - local default; override via env/secret
    POSTGRES_DB: str = "app"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI_SYNC(self) -> str:
        """Synchronous connection URL (psycopg driver) for tooling."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    # --- Redis -----------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Celery (background jobs) ---------------------------------------
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    # --- Rate limiting ---------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "200/minute"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_limit_storage_uri(self) -> str:
        return self.REDIS_URL

    # --- Observability ---------------------------------------------------
    METRICS_ENABLED: bool = True

    # --- Bootstrap superuser --------------------------------------------
    FIRST_SUPERUSER_EMAIL: str | None = None
    FIRST_SUPERUSER_PASSWORD: str | None = None

    # --- Derived helpers -------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> Settings:
        if self.is_production and self.SECRET_KEY == _INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY must be set to a strong secret in production. "
                "Generate one with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
