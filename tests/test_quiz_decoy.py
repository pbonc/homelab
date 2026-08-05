from __future__ import annotations

import http.client
import os
import sys
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "docker" / "quiz-decoy"
sys.path.insert(0, str(APP))

from decoy.profiles import PROFILES  # noqa: E402
from decoy.server import DecoyHandler, ThreadingHTTPServer  # noqa: E402


class QuizDecoyHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.previous_profile = os.environ.get("DECOY_PROFILE")
        os.environ["DECOY_PROFILE"] = "documentation"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DecoyHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        if cls.previous_profile is None:
            os.environ.pop("DECOY_PROFILE", None)
        else:
            os.environ["DECOY_PROFILE"] = cls.previous_profile

    def request(self, path: str) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        headers = {key.lower(): value for key, value in response.getheaders()}
        status = response.status
        connection.close()
        return status, headers, body

    def test_every_reviewed_profile_serves_its_declared_routes(self) -> None:
        for profile_id, profile in PROFILES.items():
            with self.subTest(profile=profile_id):
                os.environ["DECOY_PROFILE"] = profile_id
                for route in profile.routes:
                    status, headers, body = self.request(route)
                    self.assertIn(status, (200, 401))
                    self.assertTrue(body)
                    self.assertEqual(profile.server_header, headers["x-decoy-service"])

    def test_health_is_minimal_and_does_not_reveal_profile(self) -> None:
        os.environ["DECOY_PROFILE"] = "status"
        status, _, body = self.request("/health")
        self.assertEqual(200, status)
        self.assertEqual(b'{"status":"healthy"}', body)
        self.assertNotIn(b"status", body.replace(b'"status"', b""))

    def test_unknown_routes_fail_closed(self) -> None:
        os.environ["DECOY_PROFILE"] = "marketing"
        status, _, body = self.request("/admin/backup.zip")
        self.assertEqual(404, status)
        self.assertEqual(b'{"error":"not_found"}', body)

    def test_protected_work_orders_are_not_accidentally_exposed(self) -> None:
        os.environ["DECOY_PROFILE"] = "maintenance"
        status, _, body = self.request("/work-orders")
        self.assertEqual(401, status)
        self.assertEqual(b'{"error":"authentication_required"}', body)


class QuizDecoyPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (APP / "compose.yaml").read_text(encoding="utf-8")
        cls.dockerfile = (APP / "Dockerfile").read_text(encoding="utf-8")

    def test_container_is_internal_silent_and_constrained(self) -> None:
        for expected in (
            "internal: true",
            "notification_policy: never",
            'expected_vulnerable: "false"',
            "read_only: true",
            "cap_drop:",
            "no-new-privileges:true",
            "mem_limit: 48m",
            "pids_limit: 32",
        ):
            self.assertIn(expected, self.compose)
        self.assertNotIn("ports:", self.compose)
        self.assertNotIn("privileged: true", self.compose)
        self.assertNotIn("/var/run/docker.sock", self.compose)

    def test_image_is_digest_pinned_and_unprivileged(self) -> None:
        self.assertRegex(self.dockerfile, r"FROM python@sha256:[0-9a-f]{64}")
        self.assertIn("USER decoy", self.dockerfile)

    def test_catalog_contains_distinct_reviewed_profiles(self) -> None:
        self.assertEqual(7, len(PROFILES))
        self.assertEqual(len(PROFILES), len({item.title for item in PROFILES.values()}))
        self.assertEqual(
            len(PROFILES), len({item.server_header for item in PROFILES.values()})
        )


if __name__ == "__main__":
    unittest.main()
