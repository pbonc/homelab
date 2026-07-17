from __future__ import annotations

import os
import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docker" / "security-status"))

from security_status.aikido import AikidoError, issue_items, severity_counts, state_for  # noqa: E402
from security_status.config import Settings  # noqa: E402
from security_status.main import app  # noqa: E402


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


class HttpEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path: str, method: str = "GET", origin: str | None = None):
        sent = []
        received = asyncio.Queue()
        await received.put({"type": "http.request", "body": b"", "more_body": False})
        headers = [(b"origin", origin.encode())] if origin else []
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers,
        }

        async def receive():
            return await received.get()

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        return sent

    async def test_health_supports_get_and_head(self) -> None:
        get_response = await self.request("/api/health")
        head_response = await self.request("/api/health", "HEAD")
        self.assertEqual(get_response[0]["status"], 200)
        self.assertEqual(get_response[1]["body"], b'{"status":"ok"}')
        self.assertEqual(head_response[0]["status"], 200)
        self.assertEqual(head_response[1]["body"], b"")

    async def test_status_allows_configured_homepage_origin(self) -> None:
        response = await self.request("/api/status", origin="http://192.168.1.23:3000")
        headers = dict(response[0]["headers"])
        self.assertEqual(headers[b"access-control-allow-origin"], b"http://192.168.1.23:3000")

    async def test_unknown_route_is_not_found(self) -> None:
        response = await self.request("/unknown")
        self.assertEqual(response[0]["status"], 404)


if __name__ == "__main__":
    unittest.main()
