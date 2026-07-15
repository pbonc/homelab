from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


COLLECTOR_ROOT = Path(__file__).resolve().parents[1] / "docker" / "telemetry-collector"
sys.path.insert(0, str(COLLECTOR_ROOT))

from telemetry_collector.sources.ecowitt import EcowittHandler, EcowittPayloadError  # noqa: E402


FIXTURE = Path(__file__).parent / "fixtures" / "ecowitt-report.json"
RECEIVED_AT = datetime(2026, 7, 15, 18, 30, 2, tzinfo=timezone.utc)


class EcowittHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.envelope = EcowittHandler().normalize(self.payload, received_at=RECEIVED_AT)

    def test_builds_generic_versioned_envelope(self) -> None:
        self.assertEqual(self.envelope.schema_version, "1")
        self.assertEqual(self.envelope.source, "weather")
        self.assertEqual(self.envelope.handler, "ecowitt")
        self.assertEqual(self.envelope.device_id, "GW2000A_V3.2.5")
        self.assertEqual(
            self.envelope.observed_at,
            datetime(2026, 7, 15, 18, 30, tzinfo=timezone.utc),
        )

    def test_preserves_native_imperial_values(self) -> None:
        expected = {
            "outdoor_temperature": (84.7, "degF"),
            "relative_pressure": (29.982, "inHg"),
            "wind_speed": (7.2, "mph"),
            "rain_rate": (0.12, "in/h"),
            "rain_daily": (0.42, "in"),
            "solar_radiation": (615.4, "W/m2"),
        }
        for name, (value, unit) in expected.items():
            with self.subTest(name=name):
                measurement = self.envelope.measurements[name]
                self.assertEqual(measurement.value, value)
                self.assertEqual(measurement.unit, unit)

    def test_normalizes_numeric_battery_fields(self) -> None:
        battery = self.envelope.measurements["battery_wh65batt"]
        self.assertEqual(battery.value, 1.4)
        self.assertEqual(battery.unit, "source")

    def test_preserves_unknown_fields_but_redacts_secrets(self) -> None:
        self.assertEqual(self.envelope.extra_fields["runtime"], "123456")
        self.assertNotIn("PASSKEY", self.envelope.extra_fields)
        serialized = json.dumps(self.envelope.to_dict())
        self.assertNotIn("fixture-secret", serialized)

    def test_dateutc_now_uses_received_time(self) -> None:
        payload = {"dateutc": "now", "tempf": "75.0"}
        envelope = EcowittHandler().normalize(payload, received_at=RECEIVED_AT)
        self.assertEqual(envelope.observed_at, RECEIVED_AT)

    def test_rejects_invalid_numeric_measurement(self) -> None:
        with self.assertRaisesRegex(EcowittPayloadError, "tempf must be numeric"):
            EcowittHandler().normalize({"tempf": "hot"}, received_at=RECEIVED_AT)

    def test_rejects_naive_receipt_timestamp(self) -> None:
        with self.assertRaisesRegex(EcowittPayloadError, "timezone"):
            EcowittHandler().normalize(
                {"tempf": "70"},
                received_at=datetime(2026, 7, 15, 18, 30),
            )


if __name__ == "__main__":
    unittest.main()
