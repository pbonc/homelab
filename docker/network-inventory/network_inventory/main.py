from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .config import KnownInventory
from .store import InventoryStore


APP_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(
    os.environ.get("NETWORK_INVENTORY_DATABASE", APP_ROOT / "inventory.db")
)
KNOWN_PATH = Path(
    os.environ.get(
        "NETWORK_INVENTORY_KNOWN_DEVICES",
        APP_ROOT / "config" / "known-devices.json",
    )
)


def build_store() -> InventoryStore:
    return InventoryStore(
        DATABASE_PATH,
        KnownInventory(KNOWN_PATH),
        network=os.environ.get("NETWORK_INVENTORY_NETWORK", "192.168.1.0/24"),
        stale_seconds=int(
            os.environ.get("NETWORK_INVENTORY_SCAN_STALE_SECONDS", "300")
        ),
        offline_seconds=int(
            os.environ.get("NETWORK_INVENTORY_OFFLINE_SECONDS", "300")
        ),
        confirmation_seconds=int(
            os.environ.get("NETWORK_INVENTORY_CONFIRMATION_SECONDS", "300")
        ),
        private_confirmation_seconds=int(
            os.environ.get(
                "NETWORK_INVENTORY_PRIVATE_CONFIRMATION_SECONDS", "1800"
            )
        ),
    )


store = build_store()


def headers(scope: dict[str, Any], body: bytes) -> list[tuple[bytes, bytes]]:
    result = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]
    request_headers = {key.lower(): value for key, value in scope.get("headers", [])}
    origin = request_headers.get(b"origin", b"").decode("latin-1")
    if origin == "http://192.168.1.23:3000":
        result.extend(
            [
                (b"access-control-allow-origin", origin.encode("ascii")),
                (b"access-control-allow-methods", b"GET, HEAD, OPTIONS"),
                (b"access-control-allow-headers", b"Accept"),
                (b"vary", b"Origin"),
            ]
        )
    return result


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
            "headers": headers(scope, body),
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
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
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
    elif path == "/api/v1/health":
        payload = store.health(datetime.now(timezone.utc))
        payload["version"] = __version__
        await send_json(send, scope, 200, payload)
    elif path == "/api/v1/topology":
        await send_json(send, scope, 200, store.topology(datetime.now(timezone.utc)))
    else:
        await send_json(send, scope, 404, {"error": "not_found"})
