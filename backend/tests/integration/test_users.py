"""Integration tests for the user management endpoints."""

from __future__ import annotations

import uuid

import httpx
import pytest
from app.models.user import User

pytestmark = pytest.mark.integration


async def test_superuser_can_list_users(
    async_client: httpx.AsyncClient,
    superuser: User,
    superuser_token_headers: dict[str, str],
    normal_user: User,
) -> None:
    resp = await async_client.get("/api/v1/users", headers=superuser_token_headers)
    assert resp.status_code == 200
    body = resp.json()
    # Paginated envelope shape.
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["total"] == 2
    assert body["offset"] == 0
    assert isinstance(body["items"], list)
    emails = {item["email"] for item in body["items"]}
    assert {"admin@example.com", "user@example.com"} <= emails


async def test_list_honours_pagination_params(
    async_client: httpx.AsyncClient,
    superuser: User,
    superuser_token_headers: dict[str, str],
    normal_user: User,
) -> None:
    resp = await async_client.get(
        "/api/v1/users?limit=1&offset=0", headers=superuser_token_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert body["total"] == 2
    assert len(body["items"]) == 1


async def test_normal_user_cannot_list_users(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.get("/api/v1/users", headers=normal_user_token_headers)
    assert resp.status_code == 403


async def test_superuser_get_user_by_id(
    async_client: httpx.AsyncClient,
    superuser_token_headers: dict[str, str],
    normal_user: User,
) -> None:
    resp = await async_client.get(
        f"/api/v1/users/{normal_user.id}", headers=superuser_token_headers
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


async def test_get_unknown_user_returns_404(
    async_client: httpx.AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    missing = uuid.uuid4()
    resp = await async_client.get(
        f"/api/v1/users/{missing}", headers=superuser_token_headers
    )
    assert resp.status_code == 404


async def test_patch_me_updates_full_name(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.patch(
        "/api/v1/users/me",
        headers=normal_user_token_headers,
        json={"full_name": "Renamed User"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Renamed User"

    # Persisted: a follow-up read reflects the change.
    me = await async_client.get("/api/v1/users/me", headers=normal_user_token_headers)
    assert me.json()["full_name"] == "Renamed User"


async def test_normal_user_cannot_create_users(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/v1/users",
        headers=normal_user_token_headers,
        json={"email": "blocked@example.com", "password": "Blocked12345"},
    )
    assert resp.status_code == 403


async def test_superuser_can_create_user(
    async_client: httpx.AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/v1/users",
        headers=superuser_token_headers,
        json={
            "email": "created@example.com",
            "password": "CreatedPass123",
            "full_name": "Created Person",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "created@example.com"
