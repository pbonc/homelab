from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Mapping

from telemetry_collector.models import Measurement, Scalar, TelemetryEnvelope


class EcowittPayloadError(ValueError):
    """The Ecowitt payload cannot be normalized safely."""


Converter = Callable[[float], float]


def _identity(value: float) -> float:
    return value


FIELD_MAP: dict[str, tuple[str, str, Converter]] = {
    "tempf": ("outdoor_temperature", "degF", _identity),
    "tempinf": ("indoor_temperature", "degF", _identity),
    "humidity": ("outdoor_humidity", "percent", _identity),
    "humidityin": ("indoor_humidity", "percent", _identity),
    "baromrelin": ("relative_pressure", "inHg", _identity),
    "baromabsin": ("absolute_pressure", "inHg", _identity),
    "windspeedmph": ("wind_speed", "mph", _identity),
    "windgustmph": ("wind_gust", "mph", _identity),
    "winddir": ("wind_direction", "degree", _identity),
    "rainratein": ("rain_rate", "in/h", _identity),
    "eventrainin": ("rain_event", "in", _identity),
    "hourlyrainin": ("rain_hourly", "in", _identity),
    "dailyrainin": ("rain_daily", "in", _identity),
    "weeklyrainin": ("rain_weekly", "in", _identity),
    "monthlyrainin": ("rain_monthly", "in", _identity),
    "yearlyrainin": ("rain_yearly", "in", _identity),
    "uv": ("uv_index", "index", _identity),
    "solarradiation": ("solar_radiation", "W/m2", _identity),
}

SECRET_FIELDS = {"PASSKEY", "passkey", "password", "token"}
IDENTITY_FIELDS = ("stationtype", "model", "device_id", "mac")
CONTROL_FIELDS = {"dateutc", "freq", *IDENTITY_FIELDS}


def _number(value: Scalar, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EcowittPayloadError(f"{field} must be numeric") from exc


def _observed_at(value: Scalar | None, received_at: datetime) -> datetime:
    if value is None or str(value).strip().lower() == "now":
        return received_at
    text = str(value).strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise EcowittPayloadError("dateutc must be 'now' or YYYY-MM-DD HH:MM:SS") from exc
    return parsed.replace(tzinfo=timezone.utc)


class EcowittHandler:
    handler_name = "ecowitt"
    source_name = "weather"

    def normalize(
        self,
        payload: Mapping[str, Scalar],
        *,
        received_at: datetime,
    ) -> TelemetryEnvelope:
        if received_at.tzinfo is None:
            raise EcowittPayloadError("received_at must include a timezone")
        if not payload:
            raise EcowittPayloadError("payload is empty")

        device_id = next(
            (str(payload[field]) for field in IDENTITY_FIELDS if payload.get(field)),
            "ecowitt-unknown",
        )
        measurements: dict[str, Measurement] = {}
        consumed: set[str] = set()

        for source_field, (name, unit, converter) in FIELD_MAP.items():
            if source_field not in payload or payload[source_field] == "":
                continue
            converted = round(converter(_number(payload[source_field], source_field)), 4)
            measurements[name] = Measurement(value=converted, unit=unit)
            consumed.add(source_field)

        for field, value in payload.items():
            lowered = field.lower()
            if "batt" not in lowered or field in consumed or value == "":
                continue
            try:
                numeric = _number(value, field)
            except EcowittPayloadError:
                continue
            name = "battery_" + "".join(character if character.isalnum() else "_" for character in lowered)
            measurements[name] = Measurement(value=numeric, unit="source")
            consumed.add(field)

        excluded = consumed | CONTROL_FIELDS | SECRET_FIELDS
        extras = {field: value for field, value in payload.items() if field not in excluded}

        return TelemetryEnvelope(
            schema_version="1",
            source=self.source_name,
            handler=self.handler_name,
            device_id=device_id,
            observed_at=_observed_at(payload.get("dateutc"), received_at),
            received_at=received_at,
            measurements=measurements,
            extra_fields=extras,
        )
