# Makefile for the FastAPI Starter project.
#
# Run `make` or `make help` to list available targets.

# Use bash with strict flags for recipe execution.
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

# Tunables (override on the command line, e.g. `make run WORKERS=8`).
WORKERS ?= 4
HOST ?= 0.0.0.0
PORT ?= 8000
MSG ?= change me

.DEFAULT_GOAL := help

.PHONY: help install dev run worker beat migrate makemigration test cov \
        lint format typecheck up down logs build clean

help: ## Show this help message
	@echo "FastAPI Starter — available targets:"
	@echo ""
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Overridable variables: WORKERS=$(WORKERS) HOST=$(HOST) PORT=$(PORT) MSG=\"$(MSG)\""

install: ## Create a venv (if needed) and install the project with dev extras
	uv venv
	uv pip install -e ".[dev]"

dev: ## Run the development server (uvicorn, auto-reload)
	uvicorn app.main:app --host $(HOST) --port $(PORT) --reload

run: ## Run the production server (gunicorn + uvicorn workers)
	gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w $(WORKERS) -b $(HOST):$(PORT)

worker: ## Start a Celery worker
	celery -A app.worker.celery_app.celery_app worker --loglevel=info

beat: ## Start the Celery beat scheduler
	celery -A app.worker.celery_app.celery_app beat --loglevel=info

migrate: ## Apply all database migrations
	alembic upgrade head

makemigration: ## Autogenerate a new migration (override with MSG="...")
	alembic revision --autogenerate -m "$(MSG)"

test: ## Run the test suite
	pytest

cov: ## Run tests with a coverage report
	pytest --cov=app --cov-report=term-missing

lint: ## Lint the codebase with ruff
	ruff check .

format: ## Auto-format the codebase with ruff
	ruff format .

typecheck: ## Type-check the application with mypy
	mypy app

up: ## Start the Docker Compose stack in the background
	docker compose up -d

down: ## Stop the Docker Compose stack
	docker compose down

logs: ## Tail logs from the Docker Compose stack
	docker compose logs -f

build: ## Build the production Docker image
	docker build -f docker/Dockerfile -t fastapi-starter:latest .

clean: ## Remove caches, build artifacts, and coverage reports
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov \
		build dist *.egg-info
