from __future__ import annotations

import os
import sys
import unittest
import tempfile
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
        self.assertEqual(settings.storage_backend, "memory")
        self.assertEqual(settings.influxdb_bucket, "telemetry")
        self.assertIsNone(settings.influxdb_token)
        self.assertIn("http://192.168.1.23:3000", settings.allowed_origins)

    @patch.dict(os.environ, {"TELEMETRY_STALE_AFTER_SECONDS": "0"}, clear=True)
    def test_stale_threshold_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            Settings.from_environment()

    @patch.dict(os.environ, {"TELEMETRY_STORAGE_BACKEND": "unknown"}, clear=True)
    def test_storage_backend_must_be_known(self) -> None:
        with self.assertRaisesRegex(ValueError, "memory or influxdb"):
            Settings.from_environment()

    def test_influxdb_token_can_be_read_from_a_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / "token"
            secret.write_text("secret-value\n", encoding="utf-8")
            with patch.dict(os.environ, {"INFLUXDB_TOKEN_FILE": str(secret)}, clear=True):
                settings = Settings.from_environment()
        self.assertEqual(settings.influxdb_token, "secret-value")


if __name__ == "__main__":
    unittest.main()
