"""Integration tests for the image upload endpoint."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration

# Smallest valid PNG (1x1 transparent pixel).
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8ffff3f0005fe02fea73581450000000049454e44ae426082"
)


async def test_upload_and_fetch_image(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/v1/uploads",
        files={"file": ("cover.png", PNG_BYTES, "image/png")},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 201, resp.text
    url = resp.json()["url"]
    assert url.startswith("/uploads/") and url.endswith(".png")

    fetched = await async_client.get(url)
    assert fetched.status_code == 200
    assert fetched.content == PNG_BYTES


async def test_upload_rejects_non_image(
    async_client: httpx.AsyncClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    resp = await async_client.post(
        "/api/v1/uploads",
        files={"file": ("evil.png", b"#!/bin/sh\nrm -rf /", "image/png")},
        headers=normal_user_token_headers,
    )
    assert resp.status_code == 415


async def test_upload_requires_auth(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/uploads", files={"file": ("cover.png", PNG_BYTES, "image/png")}
    )
    assert resp.status_code == 401
