"""Celery application instance."""

from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging

from app.core.config import settings
from app.core.logging import configure_logging

celery_app = Celery(
    "fastapi_starter",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=270,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Example periodic task (requires `celery beat`).
celery_app.conf.beat_schedule = {
    "heartbeat-every-5-minutes": {
        "task": "app.worker.tasks.heartbeat",
        "schedule": 300.0,
    },
}


@setup_logging.connect
def _configure_celery_logging(**_kwargs: object) -> None:
    """Use the application's structlog configuration inside workers."""
    configure_logging()
