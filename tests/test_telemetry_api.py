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
        pass

    def setUp(self) -> None:
        from telemetry_collector.config import Settings
        from telemetry_collector.main import create_app
        from telemetry_collector.storage.base import MemoryTelemetryStore

        self.client = TestClient(
            create_app(store=MemoryTelemetryStore(), settings=Settings.from_environment())
        )

    def test_health_lists_registered_handler(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertIn("ecowitt", response.json()["handlers"])
        self.assertEqual(response.json()["active_source_count"], 0)

    def test_accepts_ecowitt_form_and_returns_current_weather(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        accepted = self.client.post("/data/report/", data=payload)
        self.assertEqual(accepted.status_code, 202)
        self.assertEqual(accepted.json()["source"], "weather")
        self.assertGreater(accepted.json()["measurement_count"], 10)

        current = self.client.get("/api/current/weather")
        self.assertEqual(current.status_code, 200)
        body = current.json()
        self.assertEqual(body["status"], "current")
        self.assertEqual(
            body["data"]["measurements"]["outdoor_temperature"]["unit"],
            "degF",
        )
        self.assertNotIn("PASSKEY", json.dumps(body))

        health = self.client.get("/api/health").json()
        self.assertEqual(health["active_sources"], ["weather"])
        self.assertEqual(health["active_source_count"], 1)
        self.assertIsNotNone(health["last_received_at"])

        history = self.client.get("/api/history/weather?limit=10")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["count"], 1)
        self.assertEqual(history.json()["data"][0]["source"], "weather")

    def test_rejects_wrong_content_type(self) -> None:
        response = self.client.post("/data/report/", json={"tempf": "75"})
        self.assertEqual(response.status_code, 415)

    def test_rejects_invalid_measurement(self) -> None:
        response = self.client.post("/data/report/", data={"tempf": "hot"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("tempf must be numeric", response.json()["detail"])

    def test_current_source_is_explicitly_empty_before_ingestion(self) -> None:
        response = self.client.get("/api/current/weather")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "empty")
        self.assertIsNone(response.json()["data"])

    def test_history_parameters_are_bounded(self) -> None:
        too_many = self.client.get("/api/history/weather?limit=1001")
        self.assertEqual(too_many.status_code, 422)
        too_wide = self.client.get(
            "/api/history/weather",
            params={
                "start": "2026-01-01T00:00:00Z",
                "stop": "2026-03-01T00:00:00Z",
            },
        )
        self.assertEqual(too_wide.status_code, 422)
        self.assertIn("31 days", too_wide.json()["detail"])

    def test_source_must_be_a_safe_slug(self) -> None:
        response = self.client.get("/api/current/not%20safe")
        self.assertEqual(response.status_code, 422)

    def test_health_is_unavailable_when_storage_is_down(self) -> None:
        from telemetry_collector.config import Settings
        from telemetry_collector.main import create_app
        from telemetry_collector.storage.base import MemoryTelemetryStore

        class UnhealthyStore(MemoryTelemetryStore):
            def healthy(self) -> bool:
                return False

        client = TestClient(create_app(store=UnhealthyStore(), settings=Settings.from_environment()))
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["storage"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
