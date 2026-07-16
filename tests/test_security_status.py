from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docker" / "security-status"))

from security_status.aikido import AikidoError, issue_items, severity_counts, state_for  # noqa: E402
from security_status.config import Settings  # noqa: E402


class AikidoPayloadTests(unittest.TestCase):
    def test_counts_supported_severity_shapes(self) -> None:
        payload = {
            "data": [
                {"severity": "CRITICAL"},
                {"severity_label": "high"},
                {"severity": {"name": "medium"}},
                {"severity": "low"},
                {"severity": "unknown"},
            ]
        }
        self.assertEqual(
            severity_counts(issue_items(payload)),
            {"critical": 1, "high": 1, "medium": 1, "low": 1},
        )

    def test_counts_each_issue_in_a_grouped_export_payload(self) -> None:
        payload = {"items": [{"severity": "low"}, {"severity": "low"}, {"severity": "medium"}]}
        self.assertEqual(
            severity_counts(issue_items(payload)),
            {"critical": 0, "high": 0, "medium": 1, "low": 2},
        )

    def test_rejects_unknown_list_shape(self) -> None:
        with self.assertRaises(AikidoError):
            issue_items({"unexpected": []})

    def test_state_uses_worst_open_severity(self) -> None:
        self.assertEqual(state_for({"critical": 1, "high": 2, "medium": 0, "low": 0}), "critical")
        self.assertEqual(state_for({"critical": 0, "high": 1, "medium": 2, "low": 0}), "high")
        self.assertEqual(state_for({"critical": 0, "high": 0, "medium": 1, "low": 0}), "low_medium")
        self.assertEqual(state_for({"critical": 0, "high": 0, "medium": 0, "low": 0}), "clear")


class SettingsTests(unittest.TestCase):
    def test_safe_defaults_do_not_invent_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_environment()
        self.assertIsNone(settings.client_id)
        self.assertIsNone(settings.client_secret)

    def test_rejects_aggressive_polling(self) -> None:
        with patch.dict(os.environ, {"AIKIDO_POLL_SECONDS": "30"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_environment()


if __name__ == "__main__":
    unittest.main()
