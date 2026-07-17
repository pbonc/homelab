from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from .aikido import AikidoClient, state_for
from .config import Settings


LOGGER = logging.getLogger("security-status")


class StatusCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.counts = {name: 0 for name in ("critical", "high", "medium", "low")}
        self.refreshed_at: datetime | None = None
        self.last_error: str | None = None
        self.client = (
            AikidoClient(settings.client_id, settings.client_secret)
            if settings.client_id and settings.client_secret
            else None
        )

    async def refresh(self) -> None:
        if not self.client:
            self.last_error = "Aikido credentials are not configured"
            return
        try:
            self.counts = await asyncio.to_thread(self.client.open_issue_counts)
            self.refreshed_at = datetime.now(UTC)
            self.last_error = None
        except Exception as exc:  # Cache remains available across upstream failures.
            LOGGER.warning("Aikido refresh failed: %s", type(exc).__name__)
            self.last_error = f"Aikido refresh failed: {type(exc).__name__}"

    def payload(self) -> dict[str, object]:
        now = datetime.now(UTC)
        age = (now - self.refreshed_at).total_seconds() if self.refreshed_at else None
        stale = age is not None and age > self.settings.stale_after_seconds
        if self.refreshed_at is None:
            state = "unavailable"
        elif stale:
            state = "stale"
        else:
            state = state_for(self.counts)
        return {
            "status": state,
            "scope": "workspace",
            "counts": self.counts,
            "open_total": sum(self.counts.values()),
            "last_refresh_at": self.refreshed_at.isoformat() if self.refreshed_at else None,
            "stale": stale,
            "dashboard_url": self.settings.dashboard_url,
        }


settings = Settings.from_environment()
cache = StatusCache(settings)


async def poll() -> None:
    while True:
        await cache.refresh()
        await asyncio.sleep(settings.poll_seconds)


def response_headers(scope: dict[str, Any], body: bytes) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]
    request_headers = {key.lower(): value for key, value in scope.get("headers", [])}
    origin = request_headers.get(b"origin", b"").decode("latin-1")
    if origin in settings.allowed_origins:
        headers.extend(
            [
                (b"access-control-allow-origin", origin.encode("latin-1")),
                (b"access-control-allow-methods", b"GET, HEAD, OPTIONS"),
                (b"access-control-allow-headers", b"Accept"),
                (b"vary", b"Origin"),
            ]
        )
    return headers


async def send_json(
    send: Any,
    scope: dict[str, Any],
    status: int,
    payload: dict[str, object],
) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": response_headers(scope, body),
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"" if scope.get("method") == "HEAD" else body,
        }
    )


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] == "lifespan":
        task: asyncio.Task[None] | None = None
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                task = asyncio.create_task(poll())
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                if task:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope["type"] != "http":
        return

    method = scope.get("method", "GET")
    path = scope.get("path", "")
    if method == "OPTIONS":
        await send_json(send, scope, 200, {"status": "ok"})
    elif method not in {"GET", "HEAD"}:
        await send_json(send, scope, 405, {"error": "method_not_allowed"})
    elif path == "/api/health":
        await send_json(send, scope, 200, {"status": "ok"})
    elif path == "/api/status":
        await send_json(send, scope, 200, cache.payload())
    else:
        await send_json(send, scope, 404, {"error": "not_found"})
