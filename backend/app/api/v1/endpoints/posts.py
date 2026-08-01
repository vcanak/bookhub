"""Post endpoints: feed, create, read, delete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import CurrentActiveUser, DBSession, PaginationDep
from app.schemas.common import PaginatedResponse
from app.schemas.post import PostCreate, PostRead

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[PostRead],
    summary="List posts, newest first (optionally filtered by author)",
)
async def list_posts(
    db: DBSession,
    pagination: PaginationDep,
    _: CurrentActiveUser,
    author_id: uuid.UUID | None = None,
) -> PaginatedResponse[PostRead]:
    items = await crud.post.get_feed(
        db, author_id=author_id, offset=pagination.offset, limit=pagination.limit
    )
    total = await crud.post.count_feed(db, author_id=author_id)
    return PaginatedResponse[PostRead](
        items=[PostRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post(
    "",
    response_model=PostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a post",
)
async def create_post(
    payload: PostCreate,
    db: DBSession,
    current_user: CurrentActiveUser,
) -> PostRead:
    data = payload.model_dump()
    data["author_id"] = current_user.id
    created = await crud.post.create(db, obj_in=data)
    return PostRead.model_validate(created)


@router.get("/{post_id}", response_model=PostRead, summary="Get a post by id")
async def read_post(
    post_id: uuid.UUID,
    db: DBSession,
    _: CurrentActiveUser,
) -> PostRead:
    db_post = await crud.post.get(db, id=post_id)
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return PostRead.model_validate(db_post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post (owner only)",
)
async def delete_post(
    post_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentActiveUser,
) -> None:
    db_post = await crud.post.get(db, id=post_id)
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    if db_post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )
    await crud.post.remove(db, id=post_id)
