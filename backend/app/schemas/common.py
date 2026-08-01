"""Common/shared schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    """Generic message response."""

    message: str


class HealthCheck(BaseModel):
    """Health endpoint payload."""

    status: str = "ok"
    version: str
    environment: str
    checks: dict[str, str] = Field(default_factory=dict)


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list endpoints."""

    items: list[T]
    total: int
    limit: int
    offset: int
