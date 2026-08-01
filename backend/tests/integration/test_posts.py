"""Integration tests for the post endpoints."""

from __future__ import annotations

import httpx
import pytest
from app.models.user import User

pytestmark = pytest.mark.integration

POST_PAYLOAD = {
    "title": "The Hobbit",
    "caption": "A classic adventure.",
    "rating": 5,
    "cover_image": "https://example.com/hobbit.jpg",
}


async def _create_post(
    client: httpx.AsyncClient, headers: dict[str, str], **overrides: object
) -> dict:
    resp = await client.post(
        "/api/v1/posts", json={**POST_PAYLOAD, **overrides}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_requires_all_fields(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    for missing in POST_PAYLOAD:
        payload = {k: v for k, v in POST_PAYLOAD.items() if k != missing}
        resp = await async_client.post(
            "/api/v1/posts", json=payload, headers=normal_user_token_headers
        )
        assert resp.status_code == 422, missing


async def test_feed_is_newest_first(
    async_client: httpx.AsyncClient,
    normal_user: User,
    normal_user_token_headers: dict[str, str],
) -> None:
    first = await _create_post(
        async_client, normal_user_token_headers, title="First"
    )
    second = await _create_post(
        async_client, normal_user_token_headers, title="Second"
    )
    resp = await async_client.get(
        "/api/v1/posts?limit=1&offset=0", headers=normal_user_token_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["id"] == second["id"]
    assert body["items"][0]["author"]["email"] == normal_user.email
    # Profile: filter by author.
    resp = await async_client.get(
        f"/api/v1/posts?author_id={normal_user.id}",
        headers=normal_user_token_headers,
    )
    assert {item["id"] for item in resp.json()["items"]} == {
        first["id"],
        second["id"],
    }


async def test_only_owner_can_delete(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
    superuser: User,
    create_user,
) -> None:
    created = await _create_post(async_client, normal_user_token_headers)
    other = await create_user(email="other@example.com")
    from tests.integration.conftest import _auth_headers

    resp = await async_client.delete(
        f"/api/v1/posts/{created['id']}", headers=_auth_headers(other)
    )
    assert resp.status_code == 403

    resp = await async_client.delete(
        f"/api/v1/posts/{created['id']}", headers=normal_user_token_headers
    )
    assert resp.status_code == 204

    resp = await async_client.get(
        f"/api/v1/posts/{created['id']}", headers=normal_user_token_headers
    )
    assert resp.status_code == 404
