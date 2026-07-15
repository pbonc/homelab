from __future__ import annotations

import json
import re
from datetime import datetime

from telemetry_collector.config import Settings
from telemetry_collector.models import TelemetryEnvelope
from telemetry_collector.storage.base import StorageUnavailable


def _flux_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _field_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


class InfluxDBTelemetryStore:
    def __init__(self, settings: Settings) -> None:
        if not settings.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN is required for the influxdb storage backend")
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS

        self._bucket = settings.influxdb_bucket
        self._org = settings.influxdb_org
        self._client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
            enable_gzip=True,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._query_api = self._client.query_api()

    def write(self, envelope: TelemetryEnvelope) -> None:
        from influxdb_client import Point, WritePrecision

        point = (
            Point("telemetry")
            .tag("source", envelope.source)
            .tag("handler", envelope.handler)
            .tag("device_id", envelope.device_id)
            .field("envelope_json", json.dumps(envelope.to_dict(), separators=(",", ":")))
            .field("received_at", envelope.received_at.isoformat())
            .time(envelope.observed_at, WritePrecision.NS)
        )
        for name, measurement in envelope.measurements.items():
            # InfluxDB fixes a field's type at first write. Always serialize
            # normalized measurements as floats so whole-number readings do
            # not conflict with earlier fractional readings.
            point.field(_field_name(name), float(measurement.value))
        for name, value in envelope.extra_fields.items():
            point.field(f"raw_{_field_name(name)}", value)
        try:
            self._write_api.write(bucket=self._bucket, org=self._org, record=point)
        except Exception as exc:
            raise StorageUnavailable(f"InfluxDB write failed: {exc}") from exc

    def _query_envelopes(self, flux: str) -> list[TelemetryEnvelope]:
        try:
            tables = self._query_api.query(query=flux, org=self._org)
        except Exception as exc:
            raise StorageUnavailable(f"InfluxDB query failed: {exc}") from exc
        envelopes: list[TelemetryEnvelope] = []
        for table in tables:
            for record in table.records:
                value = record.get_value()
                if isinstance(value, str):
                    envelopes.append(TelemetryEnvelope.from_dict(json.loads(value)))
        return envelopes

    def current(self, source: str) -> TelemetryEnvelope | None:
        source = _flux_string(source)
        flux = f'''
from(bucket: "{_flux_string(self._bucket)}")
  |> range(start: 0)
  |> filter(fn: (r) => r._measurement == "telemetry" and r.source == "{source}")
  |> filter(fn: (r) => r._field == "envelope_json")
  |> last()
'''.strip()
        envelopes = self._query_envelopes(flux)
        return envelopes[0] if envelopes else None

    def history(
        self,
        source: str,
        *,
        start: datetime,
        stop: datetime,
        limit: int,
    ) -> list[TelemetryEnvelope]:
        flux = f'''
from(bucket: "{_flux_string(self._bucket)}")
  |> range(start: {start.isoformat()}, stop: {stop.isoformat()})
  |> filter(fn: (r) => r._measurement == "telemetry" and r.source == "{_flux_string(source)}")
  |> filter(fn: (r) => r._field == "envelope_json")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''.strip()
        return self._query_envelopes(flux)

    def healthy(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False
