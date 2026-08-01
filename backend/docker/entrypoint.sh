#!/usr/bin/env bash
#
# Container entrypoint for the FastAPI Starter image.
#
#   1. Wait until PostgreSQL is accepting TCP connections.
#   2. Apply Alembic migrations (`alembic upgrade head`) — gated by
#      RUN_MIGRATIONS so only one service (the API) migrates by default and
#      the worker/beat replicas do not race the schema.
#   3. Hand off to the command passed by the image CMD / compose `command:`
#      via `exec "$@"` so the target process becomes PID 1 and receives
#      signals directly (clean shutdown, no zombie reaping issues).
#
# Connection details come exclusively from the environment variables defined
# in app/core/config.py (POSTGRES_SERVER, POSTGRES_PORT, ...), so there is a
# single source of truth shared with the application.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (all overridable via the environment)
# ---------------------------------------------------------------------------
POSTGRES_SERVER="${POSTGRES_SERVER:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

# Whether to run `alembic upgrade head` before starting the process.
# Defaults to true; set RUN_MIGRATIONS=false on the worker/beat services.
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

# How long to wait for Postgres before giving up.
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"
DB_WAIT_INTERVAL="${DB_WAIT_INTERVAL:-1}"

log() {
    # Timestamped log line on stderr so it interleaves cleanly with app logs.
    printf '%s [entrypoint] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

# ---------------------------------------------------------------------------
# 1. Wait for PostgreSQL using only the Python stdlib (the slim image has no
#    pg_isready / nc / curl). A plain TCP connect is enough to know the server
#    is accepting connections.
# ---------------------------------------------------------------------------
wait_for_postgres() {
    log "Waiting for PostgreSQL at ${POSTGRES_SERVER}:${POSTGRES_PORT} (timeout ${DB_WAIT_TIMEOUT}s)..."

    local elapsed=0
    until python - "$POSTGRES_SERVER" "$POSTGRES_PORT" <<'PY'
import socket
import sys

host, port = sys.argv[1], int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=3):
        sys.exit(0)
except OSError:
    sys.exit(1)
PY
    do
        if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT" ]; then
            log "ERROR: PostgreSQL not reachable after ${DB_WAIT_TIMEOUT}s. Aborting."
            exit 1
        fi
        sleep "$DB_WAIT_INTERVAL"
        elapsed=$((elapsed + DB_WAIT_INTERVAL))
    done

    log "PostgreSQL is accepting connections."
}

# ---------------------------------------------------------------------------
# 2. Apply database migrations.
# ---------------------------------------------------------------------------
run_migrations() {
    case "$(printf '%s' "$RUN_MIGRATIONS" | tr '[:upper:]' '[:lower:]')" in
        1 | true | yes | on)
            log "Applying database migrations: alembic upgrade head"
            alembic upgrade head
            log "Migrations applied."
            ;;
        *)
            log "RUN_MIGRATIONS=${RUN_MIGRATIONS}; skipping migrations."
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
wait_for_postgres
run_migrations

if [ "$#" -eq 0 ]; then
    log "ERROR: no command supplied to entrypoint."
    exit 1
fi

log "Starting: $*"
exec "$@"
