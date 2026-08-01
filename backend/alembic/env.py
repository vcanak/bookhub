"""Alembic migration environment (async).

This configures Alembic to use SQLAlchemy's async engine driven by the same
settings the application uses. The database URL is sourced from
``app.core.config.settings.SQLALCHEMY_DATABASE_URI`` (a ``postgresql+asyncpg``
URL), so there is a single source of truth for connection configuration.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

# Importing the models package registers every ORM model on ``Base.metadata``
# so that ``--autogenerate`` can detect them.
import app.models
from alembic import context

# Import application settings (connection URL) and the declarative metadata.
from app.core.config import settings
from app.db.base import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object, providing access to values within alembic.ini.
config = context.config

# Inject the runtime database URL so it never has to live in alembic.ini.
# ``%`` is escaped because ConfigParser performs interpolation on this value.
config.set_main_option(
    "sqlalchemy.url",
    settings.SQLALCHEMY_DATABASE_URI.replace("%", "%%"),
)

# Configure Python logging from the alembic.ini file, if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata used for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL (no Engine/DBAPI connection) and
    emits the migration SQL to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the context with a live connection and run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
