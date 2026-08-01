"""User management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import (
    CurrentActiveUser,
    CurrentSuperuser,
    DBSession,
    PaginationDep,
)
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def read_current_user(current_user: CurrentActiveUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead, summary="Update the current user")
async def update_current_user(
    payload: UserUpdate,
    current_user: CurrentActiveUser,
    db: DBSession,
) -> UserRead:
    # Users may not change their own active status via this route, so drop it
    # entirely (rather than setting it to None, which would be written as NULL).
    data = payload.model_dump(exclude_unset=True)
    data.pop("is_active", None)
    updated = await crud.user.update(db, db_obj=current_user, obj_in=data)
    return UserRead.model_validate(updated)


@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    summary="List users (superuser only)",
)
async def list_users(
    db: DBSession,
    pagination: PaginationDep,
    _: CurrentSuperuser,
) -> PaginatedResponse[UserRead]:
    items = await crud.user.get_multi(
        db, offset=pagination.offset, limit=pagination.limit
    )
    total = await crud.user.count(db)
    return PaginatedResponse[UserRead](
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (superuser only)",
)
async def create_user(
    payload: UserCreate,
    db: DBSession,
    _: CurrentSuperuser,
) -> UserRead:
    if await crud.user.get_by_email(db, email=payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    created = await crud.user.create(db, obj_in=payload)
    return UserRead.model_validate(created)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by id (superuser only)",
)
async def read_user(
    user_id: uuid.UUID,
    db: DBSession,
    _: CurrentSuperuser,
) -> UserRead:
    db_user = await crud.user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserRead.model_validate(db_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (superuser only)",
)
async def delete_user(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentSuperuser,
) -> None:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Superusers cannot delete themselves",
        )
    db_user = await crud.user.remove(db, id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
