from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    log_level: str
    stale_after_seconds: int
    storage_backend: str
    influxdb_url: str
    influxdb_org: str
    influxdb_bucket: str
    influxdb_token: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        stale_after = int(os.environ.get("TELEMETRY_STALE_AFTER_SECONDS", "120"))
        if stale_after <= 0:
            raise ValueError("TELEMETRY_STALE_AFTER_SECONDS must be positive")
        storage_backend = os.environ.get("TELEMETRY_STORAGE_BACKEND", "memory").lower()
        if storage_backend not in {"memory", "influxdb"}:
            raise ValueError("TELEMETRY_STORAGE_BACKEND must be memory or influxdb")
        token = os.environ.get("INFLUXDB_TOKEN")
        token_file = os.environ.get("INFLUXDB_TOKEN_FILE")
        if not token and token_file:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        return cls(
            log_level=os.environ.get("TELEMETRY_LOG_LEVEL", "INFO").upper(),
            stale_after_seconds=stale_after,
            storage_backend=storage_backend,
            influxdb_url=os.environ.get("INFLUXDB_URL", "http://influxdb:8086"),
            influxdb_org=os.environ.get("INFLUXDB_ORG", "homelab"),
            influxdb_bucket=os.environ.get("INFLUXDB_BUCKET", "telemetry"),
            influxdb_token=token,
        )
