"""Endpoints to enqueue and inspect background jobs (Celery)."""

from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import CurrentActiveUser
from app.worker.celery_app import celery_app
from app.worker.tasks import example_task

router = APIRouter()


class TaskSubmitRequest(BaseModel):
    seconds: int = 1
    message: str = "hello"


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: object | None = None


@router.post(
    "/example",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue an example background job",
)
async def submit_example_task(
    payload: TaskSubmitRequest,
    _: CurrentActiveUser,
) -> TaskSubmitResponse:
    async_result = example_task.delay(payload.seconds, payload.message)
    return TaskSubmitResponse(task_id=async_result.id, status=async_result.status)


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get the status/result of a background job",
)
async def get_task_status(
    task_id: str,
    _: CurrentActiveUser,
) -> TaskStatusResponse:
    async_result = AsyncResult(task_id, app=celery_app)
    result = async_result.result if async_result.ready() else None
    # Exceptions are not JSON-serialisable; surface their string form.
    if isinstance(result, Exception):
        result = str(result)
    return TaskStatusResponse(
        task_id=task_id,
        status=async_result.status,
        result=result,
    )
