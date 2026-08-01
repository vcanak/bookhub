"""Post CRUD operations."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.post import Post
from app.schemas.post import PostCreate


class CRUDPost(CRUDBase[Post, PostCreate, PostCreate]):
    async def get_feed(
        self,
        db: AsyncSession,
        *,
        author_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Post]:
        stmt = select(Post).order_by(Post.created_at.desc(), Post.id.desc())
        if author_id is not None:
            stmt = stmt.where(Post.author_id == author_id)
        result = await db.execute(stmt.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_feed(
        self,
        db: AsyncSession,
        *,
        author_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Post)
        if author_id is not None:
            stmt = stmt.where(Post.author_id == author_id)
        result = await db.execute(stmt)
        return int(result.scalar_one())


post = CRUDPost(Post)
