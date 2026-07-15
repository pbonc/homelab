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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TelemetryEnvelope":
        raw_measurements = payload.get("measurements")
        if not isinstance(raw_measurements, dict):
            raise ValueError("telemetry envelope measurements must be an object")
        measurements = {
            str(name): Measurement(
                value=value["value"],
                unit=str(value["unit"]),
            )
            for name, value in raw_measurements.items()
            if isinstance(value, dict)
            and isinstance(value.get("value"), (int, float))
            and "unit" in value
        }
        extras = payload.get("extra_fields", {})
        if not isinstance(extras, dict):
            raise ValueError("telemetry envelope extra_fields must be an object")
        return cls(
            schema_version=str(payload["schema_version"]),
            source=str(payload["source"]),
            handler=str(payload["handler"]),
            device_id=str(payload["device_id"]),
            observed_at=datetime.fromisoformat(str(payload["observed_at"])),
            received_at=datetime.fromisoformat(str(payload["received_at"])),
            measurements=measurements,
            extra_fields=extras,
        )
