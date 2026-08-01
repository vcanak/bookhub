"""Integration tests for the authentication flow."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_register_returns_201(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "VerySecret123",
            "full_name": "New Person",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["full_name"] == "New Person"
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert "id" in body
    # Secrets must never be returned.
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_returns_409(
    async_client: httpx.AsyncClient,
) -> None:
    payload = {"email": "dupe@example.com", "password": "VerySecret123"}
    first = await async_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await async_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_register_rejects_short_password(
    async_client: httpx.AsyncClient,
) -> None:
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


async def test_login_returns_token_pair(async_client: httpx.AsyncClient) -> None:
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "LoginPass123"},
    )
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "LoginPass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_returns_401(
    async_client: httpx.AsyncClient,
) -> None:
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "CorrectPass123"},
    )
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@example.com", "password": "NotItAtAll999"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user_returns_401(
    async_client: httpx.AsyncClient,
) -> None:
    resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401


async def test_me_with_bearer_token(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.get("/api/v1/users/me", headers=normal_user_token_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


async def test_me_without_token_returns_401(
    async_client: httpx.AsyncClient,
) -> None:
    resp = await async_client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token_returns_401(
    async_client: httpx.AsyncClient,
) -> None:
    resp = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401


async def test_refresh_flow_issues_new_tokens(
    async_client: httpx.AsyncClient,
) -> None:
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "RefreshPass123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "refresh@example.com", "password": "RefreshPass123"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await async_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_refresh_rejects_access_token(
    async_client: httpx.AsyncClient,
) -> None:
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "mixup@example.com", "password": "MixupPass123"},
    )
    login = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "mixup@example.com", "password": "MixupPass123"},
    )
    access_token = login.json()["access_token"]

    # An access token must not be accepted by the refresh endpoint.
    resp = await async_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code == 401


async def test_refresh_rejects_garbage_token(
    async_client: httpx.AsyncClient,
) -> None:
    resp = await async_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "garbage"}
    )
    assert resp.status_code == 401
