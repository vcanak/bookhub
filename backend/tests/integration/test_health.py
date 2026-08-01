"""Integration tests for the health/readiness endpoints."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_health_ok(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body


async def test_liveness(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


async def test_readiness_dependencies_ok(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"


async def test_root_metadata(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["docs"] == "/docs"
    assert "name" in body and "version" in body


async def test_openapi_schema_served(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["openapi"].startswith("3.")
