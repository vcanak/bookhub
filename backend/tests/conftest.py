"""Shared pytest configuration and test environment bootstrap.

This module MUST configure the environment before any ``app`` module is
imported, because :mod:`app.core.config` reads settings (and validates the
``SECRET_KEY`` / ``ENVIRONMENT`` guard) at import time.

Only environment setup and service-free helpers live here. Fixtures that touch
PostgreSQL / Redis live in ``tests/integration/conftest.py`` so that the unit
suite never requires external services.
"""

from __future__ import annotations

import os
import tempfile

# ---------------------------------------------------------------------------
# Environment bootstrap — keep this block ABOVE every ``app`` import.
# ---------------------------------------------------------------------------
# Force a safe test configuration. ``setdefault`` lets CI / docker-compose
# override the database and redis coordinates while keeping sane localhost
# defaults for a bare developer machine.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789-abcdefghij-please")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_JSON", "false")
# Metrics use a self-contained prometheus_client ASGI middleware (no fragile
# third-party instrumentation), so keep them enabled to exercise that path.
os.environ.setdefault("METRICS_ENABLED", "true")

os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "app")

os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

# Keep uploaded test files out of the repo tree.
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="bookhub-uploads-"))
