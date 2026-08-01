"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate
from pydantic import ValidationError

pytestmark = pytest.mark.unit


def test_user_create_valid() -> None:
    model = UserCreate(
        email="person@example.com",
        password="strong-pass-1",
        full_name="A Person",
    )
    assert model.email == "person@example.com"
    assert model.full_name == "A Person"


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="strong-pass-1")


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="person@example.com", password="short")


def test_user_create_rejects_overlong_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="person@example.com", password="x" * 129)


def test_user_update_all_fields_optional() -> None:
    model = UserUpdate()
    # Nothing was provided, so the round-trip excludes unset fields entirely.
    assert model.model_dump(exclude_unset=True) == {}


def test_user_update_partial() -> None:
    model = UserUpdate(full_name="New Name")
    assert model.model_dump(exclude_unset=True) == {"full_name": "New Name"}


def test_user_read_from_attributes() -> None:
    class _Row:
        id = uuid.uuid4()
        email = "row@example.com"
        full_name = "Row User"
        is_active = True
        is_superuser = False
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

    read = UserRead.model_validate(_Row())
    assert read.email == "row@example.com"
    assert read.is_active is True
    assert isinstance(read.id, uuid.UUID)
    # The plaintext/hashed password must never leak into the read schema.
    assert "password" not in read.model_dump()
    assert "hashed_password" not in read.model_dump()


def test_paginated_response_envelope() -> None:
    env = PaginatedResponse[UserRead](items=[], total=0, limit=50, offset=0)
    dumped = env.model_dump()
    assert set(dumped) == {"items", "total", "limit", "offset"}
    assert dumped == {"items": [], "total": 0, "limit": 50, "offset": 0}
