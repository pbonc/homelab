from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Protocol

from telemetry_collector.models import TelemetryEnvelope


class StorageUnavailable(RuntimeError):
    """The telemetry storage dependency is unavailable."""


class TelemetryStore(Protocol):
    def write(self, envelope: TelemetryEnvelope) -> None: ...

    def current(self, source: str) -> TelemetryEnvelope | None: ...

    def history(
        self,
        source: str,
        *,
        start: datetime,
        stop: datetime,
        limit: int,
    ) -> list[TelemetryEnvelope]: ...

    def healthy(self) -> bool: ...


class MemoryTelemetryStore:
    def __init__(self) -> None:
        self._records: list[TelemetryEnvelope] = []
        self._lock = Lock()

    def write(self, envelope: TelemetryEnvelope) -> None:
        with self._lock:
            self._records.append(envelope)

    def current(self, source: str) -> TelemetryEnvelope | None:
        with self._lock:
            matches = [record for record in self._records if record.source == source]
        return max(matches, key=lambda record: record.observed_at, default=None)

    def history(
        self,
        source: str,
        *,
        start: datetime,
        stop: datetime,
        limit: int,
    ) -> list[TelemetryEnvelope]:
        with self._lock:
            matches = [
                record
                for record in self._records
                if record.source == source and start <= record.observed_at < stop
            ]
        return sorted(matches, key=lambda record: record.observed_at, reverse=True)[:limit]

    def healthy(self) -> bool:
        return True
