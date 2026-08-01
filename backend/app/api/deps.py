"""Shared FastAPI dependencies (DB session, auth, pagination)."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.redis import get_redis
from app.db.session import get_session
from app.models.user import User
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

DBSession = Annotated[AsyncSession, Depends(get_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


class Pagination:
    """Reusable limit/offset pagination dependency."""

    def __init__(
        self,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> None:
        self.offset = offset
        self.limit = limit


PaginationDep = Annotated[Pagination, Depends(Pagination)]


async def get_current_user(db: DBSession, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        token_data = TokenPayload(**payload)
    except (jwt.PyJWTError, ValidationError) as exc:
        raise credentials_exception from exc

    if token_data.type != ACCESS_TOKEN_TYPE or token_data.sub is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError as exc:
        raise credentials_exception from exc

    db_user = await crud.user.get(db, id=user_id)
    if db_user is None:
        raise credentials_exception
    return db_user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUser) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]


async def get_current_superuser(current_user: CurrentActiveUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user


CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
