from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol

from telemetry_collector.models import Scalar, TelemetryEnvelope


class SourceHandler(Protocol):
    handler_name: str
    source_name: str

    def normalize(
        self,
        payload: Mapping[str, Scalar],
        *,
        received_at: datetime,
    ) -> TelemetryEnvelope: ...
