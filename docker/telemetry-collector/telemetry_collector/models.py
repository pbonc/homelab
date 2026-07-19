from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TypeAlias
from uuid import UUID


Scalar: TypeAlias = str | int | float | bool


@dataclass(frozen=True)
class DeploymentEvent:
    schema_version: str
    event_id: str
    event_type: str
    occurred_at: datetime
    service: str
    target: str
    operation: str
    result: str
    version: str
    git_commit: str
    deployer: str
    release_id: str
    rollback_performed: bool
    failure_type: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DeploymentEvent":
        required = {
            "schema_version", "event_id", "event_type", "occurred_at", "service",
            "target", "operation", "result", "version", "git_commit", "deployer",
            "release_id", "rollback_performed",
        }
        allowed = required | {"failure_type"}
        if set(payload) - allowed or required - set(payload):
            raise ValueError("deployment event fields do not match schema 1.0.0")
        if payload["schema_version"] != "1.0.0" or payload["event_type"] != "deployment":
            raise ValueError("unsupported deployment event contract")
        UUID(str(payload["event_id"]))
        occurred_at = datetime.fromisoformat(str(payload["occurred_at"]))
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        operation = str(payload["operation"])
        result = str(payload["result"])
        if operation not in {"deploy", "rollback"}:
            raise ValueError("unsupported deployment operation")
        if result not in {"successful", "failed", "rolled_back"}:
            raise ValueError("unsupported deployment result")
        failure_type = payload.get("failure_type")
        if (result == "failed") != isinstance(failure_type, str):
            raise ValueError("failed events require failure_type only")
        git_commit = str(payload["git_commit"])
        if len(git_commit) != 40 or any(char not in "0123456789abcdef" for char in git_commit):
            raise ValueError("git_commit must be a full lowercase SHA-1")
        if not isinstance(payload["rollback_performed"], bool):
            raise ValueError("rollback_performed must be boolean")
        strings = {name: str(payload[name]) for name in ("service", "target", "version", "deployer", "release_id")}
        if any(not value for value in strings.values()):
            raise ValueError("deployment event strings cannot be empty")
        return cls(
            schema_version="1.0.0", event_id=str(payload["event_id"]), event_type="deployment",
            occurred_at=occurred_at, operation=operation, result=result,
            git_commit=git_commit, rollback_performed=payload["rollback_performed"],
            failure_type=failure_type if isinstance(failure_type, str) else None, **strings,
        )


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
