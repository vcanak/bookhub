"""Post schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


class PostCreate(BaseModel):
    """Payload for creating a post. All fields required."""

    title: str = Field(min_length=1, max_length=255)
    caption: str = Field(min_length=1, max_length=2000)
    rating: int = Field(ge=1, le=5)
    cover_image: str = Field(min_length=1)


class PostRead(BaseModel):
    """Post representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    caption: str
    rating: int
    cover_image: str
    author: UserRead
    created_at: datetime
    updated_at: datetime
