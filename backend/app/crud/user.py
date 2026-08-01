"""User CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(  # type: ignore[override]
        self,
        db: AsyncSession,
        *,
        obj_in: UserCreate | dict,
    ) -> User:
        data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump()
        password = data.pop("password")
        db_obj = User(**data, hashed_password=hash_password(password))
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(  # type: ignore[override]
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate | dict,
    ) -> User:
        data = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )
        if data.get("password"):
            db_obj.hashed_password = hash_password(data.pop("password"))
        else:
            data.pop("password", None)
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> User | None:
        db_user = await self.get_by_email(db, email=email)
        if db_user is None:
            return None
        if not verify_password(password, db_user.hashed_password):
            return None
        return db_user

    @staticmethod
    def is_active(db_user: User) -> bool:
        return db_user.is_active

    @staticmethod
    def is_superuser(db_user: User) -> bool:
        return db_user.is_superuser


user = CRUDUser(User)
