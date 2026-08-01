"""Prometheus metrics via a self-contained ASGI middleware.

We deliberately avoid third-party FastAPI/Starlette instrumentation packages,
which have historically lagged behind Starlette's internal routing changes.
This middleware reads the matched route from the (shared) ASGI ``scope`` after
the application has handled the request, giving low-cardinality, templated path
labels (e.g. ``/api/v1/users/{user_id}``) without fragile route introspection.
"""

from __future__ import annotations

import time

from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

METRICS_PATH = "/metrics"

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)


class PrometheusMiddleware:
    """Pure-ASGI middleware recording request count and latency."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") == METRICS_PATH:
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = _templated_path(scope)
            elapsed = time.perf_counter() - start
            REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
            REQUEST_COUNT.labels(
                method=method, path=path, status_code=str(status_code)
            ).inc()


def _templated_path(scope: Scope) -> str:
    """Return a low-cardinality path label.

    Reconstructs the templated path (e.g. ``/api/v1/users/{user_id}``) from the
    raw request path and the matched route's ``path_params``. This is robust
    across FastAPI/Starlette versions, which differ in whether ``scope['route']``
    exposes the full path or only the leaf segment. Unmatched requests (404s)
    collapse to a single bucket to keep cardinality bounded.
    """
    if scope.get("route") is None:
        return "__unmatched__"
    raw = scope.get("path") or "/"
    params = scope.get("path_params") or {}
    if not params:
        return raw
    value_to_name = {str(value): name for name, value in params.items()}
    return "/".join(
        "{" + value_to_name[seg] + "}" if seg in value_to_name else seg
        for seg in raw.split("/")
    )


async def _metrics_endpoint(request: Request) -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app: FastAPI) -> None:
    """Register the metrics middleware and expose ``/metrics``."""
    if not settings.METRICS_ENABLED:
        return
    app.add_middleware(PrometheusMiddleware)
    app.add_api_route(
        METRICS_PATH,
        _metrics_endpoint,
        methods=["GET"],
        include_in_schema=False,
    )
