from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


COLLECTOR_ROOT = Path(__file__).resolve().parents[1] / "docker" / "telemetry-collector"
sys.path.insert(0, str(COLLECTOR_ROOT))

from telemetry_collector.models import TelemetryEnvelope  # noqa: E402
from telemetry_collector.sources.ecowitt import EcowittHandler  # noqa: E402
from telemetry_collector.storage.base import MemoryTelemetryStore  # noqa: E402
from telemetry_collector.storage.influxdb import _field_name, _flux_string  # noqa: E402


FIXTURE = Path(__file__).parent / "fixtures" / "ecowitt-report.json"


class TelemetryStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.received = datetime(2026, 7, 15, 18, 30, 2, tzinfo=timezone.utc)
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.envelope = EcowittHandler().normalize(payload, received_at=self.received)

    def test_envelope_round_trip_is_lossless(self) -> None:
        restored = TelemetryEnvelope.from_dict(self.envelope.to_dict())
        self.assertEqual(restored, self.envelope)

    def test_memory_store_current_and_history(self) -> None:
        store = MemoryTelemetryStore()
        store.write(self.envelope)
        self.assertEqual(store.current("weather"), self.envelope)
        records = store.history(
            "weather",
            start=self.envelope.observed_at - timedelta(minutes=1),
            stop=self.envelope.observed_at + timedelta(minutes=1),
            limit=10,
        )
        self.assertEqual(records, [self.envelope])

    def test_flux_values_and_field_names_are_escaped(self) -> None:
        self.assertEqual(_flux_string('weather"\\'), 'weather\\"\\\\')
        self.assertEqual(_field_name("odd field/value"), "odd_field_value")


if __name__ == "__main__":
    unittest.main()
