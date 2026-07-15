from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


COLLECTOR_ROOT = Path(__file__).resolve().parents[1] / "docker" / "telemetry-collector"
sys.path.insert(0, str(COLLECTOR_ROOT))

from telemetry_collector.config import Settings  # noqa: E402


class TelemetrySettingsTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_safe_defaults_do_not_invent_a_secret(self) -> None:
        settings = Settings.from_environment()
        self.assertEqual(settings.stale_after_seconds, 120)
        self.assertEqual(settings.influxdb_bucket, "telemetry")
        self.assertIsNone(settings.influxdb_token)

    @patch.dict(os.environ, {"TELEMETRY_STALE_AFTER_SECONDS": "0"}, clear=True)
    def test_stale_threshold_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            Settings.from_environment()


if __name__ == "__main__":
    unittest.main()
