from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _secret(name: str) -> str | None:
    value = os.environ.get(name)
    filename = os.environ.get(f"{name}_FILE")
    if not value and filename:
        value = Path(filename).read_text(encoding="utf-8").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    client_id: str | None
    client_secret: str | None
    poll_seconds: int
    stale_after_seconds: int
    allowed_origins: tuple[str, ...]
    dashboard_url: str

    @classmethod
    def from_environment(cls) -> "Settings":
        poll_seconds = int(os.environ.get("AIKIDO_POLL_SECONDS", "900"))
        stale_after_seconds = int(os.environ.get("AIKIDO_STALE_AFTER_SECONDS", "3600"))
        if poll_seconds < 60:
            raise ValueError("AIKIDO_POLL_SECONDS must be at least 60")
        if stale_after_seconds <= poll_seconds:
            raise ValueError("AIKIDO_STALE_AFTER_SECONDS must exceed AIKIDO_POLL_SECONDS")
        return cls(
            client_id=_secret("AIKIDO_CLIENT_ID"),
            client_secret=_secret("AIKIDO_CLIENT_SECRET"),
            poll_seconds=poll_seconds,
            stale_after_seconds=stale_after_seconds,
            allowed_origins=tuple(
                value.strip()
                for value in os.environ.get(
                    "AIKIDO_ALLOWED_ORIGINS",
                    "http://192.168.1.23:3000,http://brain:3000",
                ).split(",")
                if value.strip()
            ),
            dashboard_url=os.environ.get("AIKIDO_DASHBOARD_URL", "https://app.aikido.dev/"),
        )
