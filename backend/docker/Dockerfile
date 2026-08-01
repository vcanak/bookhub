# syntax=docker/dockerfile:1.7
#
# Multi-stage build for the FastAPI Starter application.
#
#   * builder : resolve and install all runtime dependencies into an isolated
#               virtualenv (/opt/venv) using `uv` for fast, reproducible installs.
#   * final   : copy the prebuilt venv + application source onto a clean slim
#               image, run as a non-root user, and serve via gunicorn.
#
# ASGI app object : app.main:app
# Listens on       : 0.0.0.0:8000

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Pull the statically-linked `uv` binary from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Compile bytecode at install time for faster cold starts in the final image.
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Target virtualenv that the final stage will copy verbatim.
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

# Create the runtime virtualenv up front so every install lands in /opt/venv.
RUN uv venv "${VENV_PATH}"

# Copy only the dependency manifest first to maximise Docker layer caching:
# this layer is only invalidated when pyproject.toml changes, not on every
# source edit. README.md is referenced by pyproject's `readme` field, so a
# lightweight placeholder is created to satisfy the build backend.
COPY pyproject.toml ./
RUN touch README.md

# Install ONLY the third-party runtime dependencies first (no dev extras, not
# the project itself) so this layer is cached until pyproject.toml changes.
# `uv pip compile` reads the static [project.dependencies] and pins them; we
# write to a file instead of using bash process substitution because Docker
# RUN uses /bin/sh, which does not support `<(...)`.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip compile pyproject.toml --output-file /tmp/requirements.txt \
    && uv pip install --python "${VENV_PATH}/bin/python" -r /tmp/requirements.txt

# Copy the application source and install the project itself (editable-free).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python "${VENV_PATH}/bin/python" --no-deps .

# ---------------------------------------------------------------------------
# Stage 2 — final runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    APP_HOME=/app

# Create an unprivileged user/group to run the application.
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --home-dir "${APP_HOME}" \
        --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR ${APP_HOME}

# Copy the prebuilt virtualenv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy application source, migrations and entrypoint with correct ownership.
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

USER appuser

EXPOSE 8000

# Liveness check using the stdlib (slim has no curl/wget). Hits the dedicated
# liveness probe, which never touches downstream dependencies.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health/live', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command: production-grade gunicorn with Uvicorn workers.
# Override (e.g. for the Celery worker/beat) via docker-compose `command:`.
# gunicorn 26's control socket is placed under the writable /tmp so it works
# for the non-root user and with a read-only root filesystem (k8s).
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--graceful-timeout", "30", \
     "--timeout", "60", \
     "--control-socket", "/tmp/gunicorn.ctl"]
