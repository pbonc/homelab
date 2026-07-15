from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    log_level: str
    stale_after_seconds: int
    influxdb_url: str
    influxdb_org: str
    influxdb_bucket: str
    influxdb_token: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        stale_after = int(os.environ.get("TELEMETRY_STALE_AFTER_SECONDS", "120"))
        if stale_after <= 0:
            raise ValueError("TELEMETRY_STALE_AFTER_SECONDS must be positive")
        return cls(
            log_level=os.environ.get("TELEMETRY_LOG_LEVEL", "INFO").upper(),
            stale_after_seconds=stale_after,
            influxdb_url=os.environ.get("INFLUXDB_URL", "http://influxdb:8086"),
            influxdb_org=os.environ.get("INFLUXDB_ORG", "homelab"),
            influxdb_bucket=os.environ.get("INFLUXDB_BUCKET", "telemetry"),
            influxdb_token=os.environ.get("INFLUXDB_TOKEN"),
        )
