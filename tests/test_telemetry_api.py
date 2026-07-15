from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


COLLECTOR_ROOT = Path(__file__).resolve().parents[1] / "docker" / "telemetry-collector"
sys.path.insert(0, str(COLLECTOR_ROOT))

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient = None  # type: ignore[assignment,misc]


FIXTURE = Path(__file__).parent / "fixtures" / "ecowitt-report.json"


@unittest.skipIf(TestClient is None, "telemetry API test dependencies are not installed")
class TelemetryApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from telemetry_collector.main import app

        cls.client = TestClient(app)

    def setUp(self) -> None:
        from telemetry_collector.main import latest

        latest.clear()

    def test_health_lists_registered_handler(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertIn("ecowitt", response.json()["handlers"])

    def test_accepts_ecowitt_form_and_returns_current_weather(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        accepted = self.client.post("/data/report/", data=payload)
        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(accepted.json()["source"], "weather")
        self.assertGreater(accepted.json()["measurement_count"], 10)

        current = self.client.get("/api/current/weather")
        self.assertEqual(current.status_code, 200)
        body = current.json()
        self.assertEqual(body["measurements"]["outdoor_temperature"]["unit"], "degF")
        self.assertNotIn("PASSKEY", json.dumps(body))

    def test_rejects_wrong_content_type(self) -> None:
        response = self.client.post("/data/report/", json={"tempf": "75"})
        self.assertEqual(response.status_code, 415)

    def test_rejects_invalid_measurement(self) -> None:
        response = self.client.post("/data/report/", data={"tempf": "hot"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("tempf must be numeric", response.json()["detail"])

    def test_current_source_is_explicitly_empty_before_ingestion(self) -> None:
        response = self.client.get("/api/current/weather")
        self.assertEqual(response.status_code, 404)
        self.assertIn("no telemetry available", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
