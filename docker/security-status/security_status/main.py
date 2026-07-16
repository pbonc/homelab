from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
            AikidoClient(settings.client_id, settings.client_secret, settings.repository)
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
            "repository": self.settings.repository,
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(poll())
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Homelab Security Status", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["GET"],
    allow_headers=["Accept"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict[str, object]:
    return cache.payload()
