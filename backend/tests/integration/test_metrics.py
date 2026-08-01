"""Tests for the Prometheus /metrics endpoint."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_metrics_endpoint_exposes_request_metrics(
    async_client: httpx.AsyncClient,
) -> None:
    # Generate at least one measured request first.
    await async_client.get("/api/v1/health/live")

    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]

    body = resp.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    # The templated path label keeps cardinality bounded.
    assert "/api/v1/health/live" in body
