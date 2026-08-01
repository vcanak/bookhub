"""Authentication endpoints: register, login, refresh."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import DBSession
from app.core.rate_limit import limiter
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.token import RefreshRequest, Token, TokenPayload
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


def _issue_token_pair(subject: str) -> Token:
    return Token(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    payload: UserCreate,
    db: DBSession,
) -> UserRead:
    existing = await crud.user.get_by_email(db, email=payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    new_user = await crud.user.create(db, obj_in=payload)
    return UserRead.model_validate(new_user)


@router.post("/login", response_model=Token, summary="Obtain access/refresh tokens")
@limiter.limit("20/minute")
async def login(
    request: Request,
    response: Response,
    db: DBSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    db_user = await crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return _issue_token_pair(str(db_user.id))


@router.post("/refresh", response_model=Token, summary="Refresh an access token")
@limiter.limit("60/minute")
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: DBSession,
) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(body.refresh_token)
        token_data = TokenPayload(**payload)
    except (jwt.PyJWTError, ValueError) as exc:
        raise credentials_exception from exc

    if token_data.type != REFRESH_TOKEN_TYPE or token_data.sub is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError as exc:
        raise credentials_exception from exc

    db_user = await crud.user.get(db, id=user_id)
    if db_user is None or not db_user.is_active:
        raise credentials_exception
    return _issue_token_pair(str(db_user.id))
