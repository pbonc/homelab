from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TypeAlias


Scalar: TypeAlias = str | int | float | bool


@dataclass(frozen=True)
class Measurement:
    value: int | float
    unit: str


@dataclass(frozen=True)
class TelemetryEnvelope:
    schema_version: str
    source: str
    handler: str
    device_id: str
    observed_at: datetime
    received_at: datetime
    measurements: dict[str, Measurement]
    extra_fields: dict[str, Scalar] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.isoformat()
        payload["received_at"] = self.received_at.isoformat()
        return payload
