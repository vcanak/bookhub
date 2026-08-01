# FastAPI Starter

[![CI](https://github.com/your-org/fastapi-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/fastapi-starter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

A production-grade [FastAPI](https://fastapi.tiangolo.com/) starter template wired
end-to-end: async PostgreSQL, Redis, Celery background jobs, JWT authentication,
structured logging, Prometheus metrics, rate limiting, Docker/Compose, Kubernetes
manifests, a Helm chart, and a full CI pipeline. Clone it, copy `.env.example`,
and you have a real service running in minutes.

---

## Features

- **FastAPI** application factory (`app.main:app`) with versioned routing under `/api/v1`.
- **PostgreSQL** via **SQLAlchemy 2.x** async ORM (`asyncpg` driver) with typed `Mapped` models.
- **Alembic** async migrations with a deterministic constraint naming convention.
- **Redis** for caching, rate-limit storage, and as the Celery broker/result backend.
- **JWT authentication** (access + refresh tokens) with `bcrypt` password hashing.
- **Celery** background jobs with a worker and `beat` scheduler (example periodic task included).
- **Docker** multi-stage build (`python:3.12-slim`, non-root user) and a Compose stack.
- **Unit + integration tests** with `pytest` / `pytest-asyncio` and coverage reporting.
- **GitHub Actions** CI: lint, type check, tests against real Postgres/Redis, and a Docker build.
- **OpenAPI** docs at `/docs` (Swagger UI) and `/redoc` (ReDoc).
- **structlog** structured logging (JSON in production, console-friendly in dev).
- **pydantic-settings** strongly-typed configuration from environment variables.
- **Health endpoints** for liveness and readiness probes (readiness returns `503` when dependencies are down).
- **slowapi** rate limiting backed by Redis.
- **Prometheus metrics** exposed at `/metrics`.
- **Kubernetes manifests** (`k8s/`) and a **Helm chart** (`helm/`) for deployment.

---

## Architecture overview

The app is built with a classic layered structure. An ASGI server (Uvicorn in dev,
Gunicorn with Uvicorn workers in prod) serves the FastAPI app. Requests flow through
middleware (request-context logging, rate limiting, CORS, metrics) into versioned
routers, which call CRUD/service code that talks to PostgreSQL over an async
SQLAlchemy engine. Redis backs rate limiting and acts as the Celery broker/result
backend. Long-running work is offloaded to Celery workers; periodic work is driven
by Celery beat. Observability is provided by structured logs and a Prometheus
metrics endpoint.

```
                 ┌──────────────┐
   HTTP ───────► │  Gunicorn /  │
                 │   Uvicorn    │
                 └──────┬───────┘
                        │  ASGI (app.main:app)
                 ┌──────▼───────────────────────────────────┐
                 │ Middleware: request-context · rate limit  │
                 │            · CORS · Prometheus metrics     │
                 └──────┬───────────────────────────────────┘
                        │
              ┌─────────▼─────────┐         ┌──────────────────┐
              │  API v1 routers   │         │  Celery worker /  │
              │  auth · users     │         │  beat             │
              │  health · tasks   │         └─────────┬────────┘
              └────┬─────────┬────┘                   │
                   │         │  enqueue                │
            ┌──────▼───┐ ┌───▼────────────────────────▼───┐
            │ Postgres │ │            Redis               │
            │ (async)  │ │ rate-limit · broker · backend  │
            └──────────┘ └────────────────────────────────┘
```

### Project structure

```text
fast_api_starter/
├── app/                          # Application package (ASGI app = app.main:app)
│   ├── main.py                   # App factory + ASGI entrypoint
│   ├── api/
│   │   ├── deps.py               # Shared dependencies (DB session, current user, pagination)
│   │   └── v1/
│   │       ├── router.py         # Aggregate API v1 router
│   │       └── endpoints/        # auth.py · users.py · health.py · tasks.py
│   ├── core/
│   │   ├── config.py             # pydantic-settings Settings (source of truth for env vars)
│   │   ├── logging.py            # structlog configuration
│   │   ├── metrics.py            # Prometheus instrumentation (/metrics)
│   │   ├── middleware.py         # Request-context / access-log middleware
│   │   ├── rate_limit.py         # slowapi limiter
│   │   └── security.py           # JWT + password hashing
│   ├── crud/                     # Data-access layer (base.py, user.py)
│   ├── db/
│   │   ├── base.py               # Declarative Base + naming convention + TimestampMixin
│   │   ├── session.py            # Async engine / session factory
│   │   └── redis.py              # Redis connection pool
│   ├── models/                   # SQLAlchemy ORM models (user.py)
│   ├── schemas/                  # Pydantic schemas (user, token, common)
│   └── worker/
│       ├── celery_app.py         # Celery app object (app.worker.celery_app.celery_app)
│       └── tasks.py              # Example + periodic tasks
├── alembic/                      # Async migration environment
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── tests/
│   ├── unit/                     # Pure unit tests (no external services)
│   └── integration/              # Tests requiring Postgres / Redis
├── docker/
│   └── Dockerfile                # Multi-stage production image
├── k8s/                          # Kubernetes manifests (namespace, configmap, ...)
├── helm/
│   └── fastapi-starter/          # Helm chart
├── .github/
│   └── workflows/                # ci.yml · release.yml
├── pyproject.toml                # Dependencies + tool config (ruff, mypy, pytest, coverage)
├── .env.example                  # Reference for all environment variables
├── Makefile                      # Developer convenience targets
└── README.md
```

---

## Quickstart with Docker Compose

The fastest path to a running stack (API + Postgres + Redis + Celery):

```bash
# 1. Copy the environment template and adjust values if you like.
cp .env.example .env

# 2. Build and start the stack in the background.
docker compose up -d --build

# 3. Apply database migrations (first run only, or after a schema change).
docker compose exec api alembic upgrade head

# 4. Open the interactive API docs.
open http://localhost:8000/docs        # macOS (use your browser otherwise)
```

The API listens on **port 8000**. With the Compose defaults, `POSTGRES_SERVER=postgres`
and `REDIS_HOST=redis` resolve to the Compose service names automatically.

Tear it all down with:

```bash
docker compose down            # stop containers
docker compose down -v         # also remove named volumes (wipes the database)
```

---

## Local development with uv

This project uses [`uv`](https://github.com/astral-sh/uv) as its package manager.
You will need a local PostgreSQL and Redis (or just run those two via Compose while
developing the app on bare metal).

```bash
# 1. Create and activate a virtual environment.
uv venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install the project with dev extras (editable install).
uv pip install -e ".[dev]"

# 3. Configure your environment.
cp .env.example .env
# For bare-metal local dev, set POSTGRES_SERVER=localhost and REDIS_HOST=localhost.

# 4. Apply database migrations.
alembic upgrade head

# 5. Run the dev server with auto-reload.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit <http://localhost:8000/docs> for Swagger UI and <http://localhost:8000/redoc>
for ReDoc.

> Most of these steps are wrapped in the [`Makefile`](./Makefile) — run `make help`
> to see every target.

### Production server

In production the app is served by Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

---

## Running tests

The test suite is split into `unit` and `integration` markers. Integration tests
require a reachable PostgreSQL and Redis.

```bash
pytest                              # run the full suite
pytest -m unit                      # only pure unit tests
pytest -m integration               # only tests that need Postgres/Redis
pytest --cov=app --cov-report=term  # with coverage
```

`pytest-asyncio` runs in `auto` mode, so `async def` tests need no extra decorators.

---

## Linting, formatting & type checking

[`ruff`](https://docs.astral.sh/ruff/) handles both linting and formatting;
[`mypy`](https://mypy-lang.org/) provides static type checking.

```bash
ruff check .          # lint
ruff format .         # auto-format (use --check in CI)
mypy app              # type check the application package
```

These exact commands run in CI on every push and pull request.

---

## Environment variable reference

All settings are defined in [`app/core/config.py`](./app/core/config.py) and loaded
from the environment (and an optional `.env` file). Variable names are
**case-sensitive**. See [`.env.example`](./.env.example) for a ready-to-copy template.

| Variable | Description | Default |
| --- | --- | --- |
| `PROJECT_NAME` | Human-readable application name. | `FastAPI Starter` |
| `VERSION` | Application version (shown in docs & health). | `0.1.0` |
| `DESCRIPTION` | Application description for OpenAPI. | `Production-grade FastAPI starter.` |
| `API_V1_PREFIX` | URL prefix for v1 routes. | `/api/v1` |
| `ENVIRONMENT` | One of `local`, `development`, `staging`, `production`, `test`. | `local` |
| `DEBUG` | Enable FastAPI debug mode. | `false` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, ...). | `INFO` |
| `LOG_JSON` | Emit logs as JSON (vs. console-friendly). | `true` |
| `SECRET_KEY` | JWT signing key, **min 32 chars**. Must be strong in production. | *insecure dev default* |
| `ALGORITHM` | JWT signing algorithm. | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (minutes). | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (days). | `7` |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins (comma-separated or JSON list). | *(empty)* |
| `POSTGRES_SERVER` | PostgreSQL host. | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port. | `5432` |
| `POSTGRES_USER` | PostgreSQL user. | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password. | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name. | `app` |
| `DB_POOL_SIZE` | SQLAlchemy connection pool size. | `10` |
| `DB_MAX_OVERFLOW` | Extra connections allowed beyond the pool size. | `20` |
| `DB_POOL_PRE_PING` | Test connections before use (avoids stale connections). | `true` |
| `DB_ECHO` | Echo SQL statements to logs (debugging). | `false` |
| `REDIS_HOST` | Redis host. | `localhost` |
| `REDIS_PORT` | Redis port. | `6379` |
| `REDIS_DB` | Redis database index. | `0` |
| `REDIS_PASSWORD` | Redis password (optional). | *(none)* |
| `CELERY_BROKER_URL` | Celery broker URL. Falls back to `REDIS_URL` if unset. | *(derived from Redis)* |
| `CELERY_RESULT_BACKEND` | Celery result backend URL. Falls back to `REDIS_URL` if unset. | *(derived from Redis)* |
| `RATE_LIMIT_ENABLED` | Enable slowapi rate limiting. | `true` |
| `RATE_LIMIT_DEFAULT` | Default rate limit applied globally. | `200/minute` |
| `METRICS_ENABLED` | Expose Prometheus metrics at `/metrics`. | `true` |
| `FIRST_SUPERUSER_EMAIL` | Optional bootstrap superuser email. | *(none)* |
| `FIRST_SUPERUSER_PASSWORD` | Optional bootstrap superuser password. | *(none)* |

> The database URLs (`SQLALCHEMY_DATABASE_URI`, `SQLALCHEMY_DATABASE_URI_SYNC`) and
> `REDIS_URL` are **computed** from the variables above — you do not set them directly.

---

## API overview

All endpoints are mounted under the `API_V1_PREFIX` (default `/api/v1`).

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | none | Register a new user. |
| `POST` | `/api/v1/auth/login` | none | Exchange credentials for an access + refresh token pair. |
| `POST` | `/api/v1/auth/refresh` | refresh token | Issue a fresh token pair from a valid refresh token. |
| `GET` | `/api/v1/users/me` | access token | Get the current user. |
| `PATCH` | `/api/v1/users/me` | access token | Update the current user. |
| `GET` | `/api/v1/users` | superuser | List users (paginated). |
| `POST` | `/api/v1/users` | superuser | Create a user. |
| `GET` | `/api/v1/users/{user_id}` | superuser | Get a user by id. |
| `DELETE` | `/api/v1/users/{user_id}` | superuser | Delete a user by id. |
| `GET` | `/api/v1/health` | none | Basic health check. |
| `GET` | `/api/v1/health/live` | none | Liveness probe (process is up). |
| `GET` | `/api/v1/health/ready` | none | Readiness probe — returns `503` if DB/Redis are down. |
| `POST` | `/api/v1/tasks/example` | access token | Enqueue an example background job (`202 Accepted`). |
| `GET` | `/api/v1/tasks/{task_id}` | access token | Get the status/result of a background job. |

Interactive docs and the OpenAPI schema:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/api/v1/openapi.json`

### Authentication flow

```bash
# Register a user.
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"correct horse battery staple","full_name":"Alice"}'

# Log in (OAuth2 password form) to obtain tokens.
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=alice@example.com&password=correct horse battery staple'

# Call an authenticated endpoint.
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## Background jobs (Celery)

Celery uses Redis as both the broker and the result backend (derived from your
Redis settings unless `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` are set).

```bash
# Start a worker.
celery -A app.worker.celery_app.celery_app worker --loglevel=info

# Start the beat scheduler (drives periodic tasks, e.g. the example heartbeat).
celery -A app.worker.celery_app.celery_app beat --loglevel=info
```

Enqueue the example task via the API (`POST /api/v1/tasks/example`) and poll its
status with `GET /api/v1/tasks/{task_id}`.

---

## Observability

- **Metrics:** Prometheus metrics are exposed at `GET /metrics` (toggle with
  `METRICS_ENABLED`). Point a Prometheus scrape job at this endpoint and visualize
  request rates, latencies, and error counts in Grafana.
- **Logs:** Structured logging via `structlog`. Set `LOG_JSON=true` for
  machine-parseable JSON (ideal for production log pipelines) or `false` for
  human-friendly console output during development. Control verbosity with
  `LOG_LEVEL`. Each request is tagged with a request-context id by the middleware.
- **Health:** Use `GET /api/v1/health/live` as a Kubernetes liveness probe and
  `GET /api/v1/health/ready` as a readiness probe — the latter checks PostgreSQL
  and Redis and returns `503` when a dependency is unreachable.

---

## Deployment

### Docker image

```bash
# Build the production image (multi-stage, runs as a non-root user).
docker build -f docker/Dockerfile -t fastapi-starter:latest .

# Run it (provide configuration via environment variables).
docker run --rm -p 8000:8000 --env-file .env fastapi-starter:latest
```

The image's default command is the production Gunicorn invocation; override the
`command` for the Celery worker/beat in Compose or your orchestrator.

### Kubernetes

Raw manifests live in [`k8s/`](./k8s):

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/                 # configmap and the rest of the stack
```

The provided `ConfigMap` maps 1:1 to the environment variables in
`app/core/config.py`. Secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`, ...) must be
supplied via a Kubernetes `Secret`, not committed to the repo.

### Helm

A chart is provided in [`helm/fastapi-starter/`](./helm/fastapi-starter):

```bash
helm install fastapi-starter ./helm/fastapi-starter \
  --namespace fastapi-starter --create-namespace \
  --set secret.SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

The chart expects PostgreSQL and Redis to be provided externally (managed services
or pre-existing in-cluster releases); see `helm/fastapi-starter/Chart.yaml` for
details on optionally bundling the Bitnami subcharts.

---

## Security note: `SECRET_KEY` in production

`SECRET_KEY` signs and verifies JWTs. The repository ships with an **insecure
development default**, and the application **refuses to start in production**
(`ENVIRONMENT=production`) while that default is in place.

Always generate a strong, unique value before deploying:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Provide it via an environment variable or a secrets manager — never commit it to
version control. Treat `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and
`FIRST_SUPERUSER_PASSWORD` the same way.

---

## License

Released under the [MIT License](./LICENSE).
