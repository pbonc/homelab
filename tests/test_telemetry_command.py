from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from labctl.commands import telemetry


class TelemetryCommandTests(unittest.TestCase):
    @patch("labctl.commands.telemetry._container_status")
    @patch("labctl.commands.telemetry._get_json")
    def test_reports_health_and_imperial_weather(self, get_json, container_status) -> None:
        container_status.return_value = {
            "status": "healthy", "state": "running", "health": "healthy", "level": "pass"
        }
        get_json.side_effect = [
            {"status": "healthy", "active_source_count": 1, "last_received_at": "2026-07-15T20:00:00Z"},
            {
                "status": "current", "age_seconds": 4.2,
                "data": {"measurements": {"outdoor_temperature": {"value": 82.4, "unit": "degF"}}},
            },
        ]
        output = io.StringIO()
        with patch("sys.stdout", output):
            result = telemetry.run_telemetry()
        self.assertEqual(result, 0)
        self.assertIn("82.4 degF", output.getvalue())
        self.assertIn("Active sources: 1", output.getvalue())

    @patch("labctl.commands.telemetry._container_status")
    @patch("labctl.commands.telemetry._get_json", side_effect=RuntimeError("offline"))
    def test_returns_failure_when_api_is_offline(self, _get_json, container_status) -> None:
        container_status.return_value = {
            "status": "unhealthy", "state": "not-found", "health": "unknown", "level": "fail"
        }
        self.assertEqual(telemetry.run_telemetry(), 1)


if __name__ == "__main__":
    unittest.main()
