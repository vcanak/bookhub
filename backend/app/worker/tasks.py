"""Example Celery tasks."""

from __future__ import annotations

import time
from typing import Any

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger("app.worker.tasks")


@celery_app.task(
    name="app.worker.tasks.example_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def example_task(self: Any, seconds: int, message: str) -> dict[str, Any]:
    """A trivial task that simulates work and returns a result."""
    logger.info("example_task_started", task_id=self.request.id, seconds=seconds)
    time.sleep(min(max(seconds, 0), 10))
    logger.info("example_task_completed", task_id=self.request.id)
    return {"message": message, "slept_seconds": min(max(seconds, 0), 10)}


@celery_app.task(name="app.worker.tasks.heartbeat")
def heartbeat() -> dict[str, str]:
    """Periodic no-op task wired to celery beat for liveness signalling."""
    logger.debug("worker_heartbeat")
    return {"status": "ok"}
