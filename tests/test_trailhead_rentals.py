from __future__ import annotations

import http.client
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "docker" / "trailhead-rentals"
sys.path.insert(0, str(APP))

from trailhead.data import Review  # noqa: E402
from trailhead.features import FeatureVariants, load_variant_set  # noqa: E402
from trailhead.server import (  # noqa: E402
    SUBMITTED_REVIEWS,
    SUPPORT_TICKETS,
    TrailheadHandler,
    ThreadingHTTPServer,
)
from trailhead.service import (  # noqa: E402
    admin_summary,
    profile_for_user,
    rental_for_user,
    search_products,
)


class TrailheadServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.variants = FeatureVariants()

    def test_secure_search_returns_matching_synthetic_products(self) -> None:
        results = search_products("water", self.variants)
        self.assertEqual(["Current Solo Kayak"], [item.name for item in results])

    def test_rental_lookup_enforces_owner_and_hides_existence(self) -> None:
        self.assertIsNotNone(rental_for_user("alex", 72041, self.variants))
        self.assertIsNone(rental_for_user("alex", 72042, self.variants))
        self.assertIsNone(rental_for_user("alex", 99999, self.variants))

    def test_profile_projection_excludes_password_and_role(self) -> None:
        profile = profile_for_user("alex", self.variants)
        self.assertEqual({"username", "name", "email"}, set(profile))

    def test_admin_summary_requires_admin_role(self) -> None:
        self.assertIsNone(admin_summary("alex", self.variants))
        self.assertEqual(3, admin_summary("ranger", self.variants)["active_rentals"])

    def test_unreviewed_variant_set_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown or unreviewed"):
            load_variant_set("mystery")

    def test_idor_variant_changes_only_object_authorization(self) -> None:
        lesson = load_variant_set("lesson-idor")
        self.assertIsNotNone(rental_for_user("alex", 72042, lesson))
        self.assertEqual("parameterized", lesson.search)
        self.assertEqual("encoded", lesson.review_rendering)

    def test_sql_injection_variant_changes_query_logic(self) -> None:
        payload = "' OR 1=1 --"
        self.assertEqual([], search_products(payload, self.variants))
        lesson_results = search_products(payload, load_variant_set("lesson-sqli"))
        self.assertEqual(6, len(lesson_results))

    def test_reviewed_combination_changes_only_selected_seams(self) -> None:
        combined = load_variant_set("lesson-idor-sqli-stored-xss")
        self.assertEqual("authentication-only", combined.rental_authorization)
        self.assertEqual("concatenated-sql", combined.search)
        self.assertEqual("raw", combined.review_rendering)
        self.assertEqual("allowlisted", combined.profile_updates)
        self.assertEqual("minimal", combined.api_projection)
        self.assertEqual("role-required", combined.admin_authorization)


class TrailheadHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["TRAILHEAD_VARIANT_SET"] = "secure-baseline"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), TrailheadHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        SUBMITTED_REVIEWS.clear()
        SUPPORT_TICKETS.clear()

    def request(
        self,
        method: str,
        path: str,
        body: str | None = None,
        cookie: str | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if cookie:
            headers["Cookie"] = cookie
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        result_headers = {key.lower(): value for key, value in response.getheaders()}
        status = response.status
        connection.close()
        return status, result_headers, payload

    def login(self, username: str = "alex", password: str = "trail-only-41") -> str:
        status, headers, _ = self.request(
            "POST", "/login", urlencode({"username": username, "password": password})
        )
        self.assertEqual(303, status)
        return headers["set-cookie"].split(";", 1)[0]

    def test_home_catalog_css_and_health_are_available(self) -> None:
        status, headers, body = self.request("GET", "/")
        self.assertEqual(200, status)
        self.assertIn(b"Good gear. No garage required.", body)
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
        self.assertEqual(200, self.request("GET", "/static/app.css")[0])
        health = json.loads(self.request("GET", "/api/health")[2])
        self.assertEqual({"status": "healthy"}, health)
        self.assertNotIn(b"variant", self.request("GET", "/api/health")[2])

    def test_catalog_api_is_minimal_and_searchable(self) -> None:
        status, _, body = self.request("GET", "/api/catalog?q=bike")
        payload = json.loads(body)
        self.assertEqual(200, status)
        self.assertEqual("Switchback Trail Bike", payload[0]["name"])
        self.assertEqual({"id", "name", "category", "daily_rate"}, set(payload[0]))

    def test_login_uses_opaque_session_and_rental_api_enforces_owner(self) -> None:
        cookie = self.login()
        self.assertNotIn("alex", cookie)
        self.assertEqual(200, self.request("GET", "/api/rentals/72041", cookie=cookie)[0])
        denied = self.request("GET", "/api/rentals/72042", cookie=cookie)
        missing = self.request("GET", "/api/rentals/99999", cookie=cookie)
        self.assertEqual((404, b'{"error": "not_found"}'), (denied[0], denied[2]))
        self.assertEqual((missing[0], missing[2]), (denied[0], denied[2]))

    def test_member_is_forbidden_from_admin_surface(self) -> None:
        cookie = self.login()
        self.assertEqual(403, self.request("GET", "/api/admin/summary", cookie=cookie)[0])
        self.assertEqual(403, self.request("GET", "/admin", cookie=cookie)[0])

    def test_admin_can_access_summary(self) -> None:
        cookie = self.login("ranger", "trail-admin-19")
        status, _, body = self.request("GET", "/api/admin/summary", cookie=cookie)
        self.assertEqual(200, status)
        self.assertEqual(3, json.loads(body)["active_rentals"])

    def test_review_content_is_encoded_on_render(self) -> None:
        SUBMITTED_REVIEWS.append(Review("Alex", "tent-alpine-2", 5, "<script>alert(1)</script>"))
        _, _, body = self.request("GET", "/reviews")
        self.assertNotIn(b"<script>alert(1)</script>", body)
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", body)

    def test_stored_xss_variant_emits_saved_markup(self) -> None:
        previous = os.environ["TRAILHEAD_VARIANT_SET"]
        os.environ["TRAILHEAD_VARIANT_SET"] = "lesson-stored-xss"
        try:
            SUBMITTED_REVIEWS.append(
                Review("Alex", "tent-alpine-2", 5, "<script>document.title='field-note'</script>")
            )
            _, headers, body = self.request("GET", "/reviews")
            self.assertIn(b"<script>document.title='field-note'</script>", body)
            self.assertIn("'unsafe-inline'", headers["content-security-policy"])
        finally:
            os.environ["TRAILHEAD_VARIANT_SET"] = previous

    def test_support_submission_is_bounded_and_memory_only(self) -> None:
        status, _, body = self.request(
            "POST",
            "/support",
            urlencode({"name": "A", "email": "a@example.test", "message": "Fit question"}),
        )
        self.assertEqual(202, status)
        self.assertIn(b"disappears when the container stops", body)
        self.assertEqual(1, len(SUPPORT_TICKETS))

    def test_static_path_traversal_is_rejected(self) -> None:
        self.assertEqual(404, self.request("GET", "/static/../trailhead/data.py")[0])


class TrailheadContainerPolicyTests(unittest.TestCase):
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
            "mem_limit: 96m",
            "pids_limit: 64",
        ):
            self.assertIn(expected, self.compose)
        self.assertNotIn("ports:", self.compose)
        self.assertNotIn("privileged: true", self.compose)
        self.assertNotIn("/var/run/docker.sock", self.compose)

    def test_image_base_is_digest_pinned_and_process_is_unprivileged(self) -> None:
        self.assertRegex(self.dockerfile, r"FROM python@sha256:[0-9a-f]{64}")
        self.assertIn("USER trailhead", self.dockerfile)

    def test_private_answer_keys_cover_three_reviewed_classes(self) -> None:
        templates = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((APP / "variants").glob("*.json"))
        ]
        self.assertEqual(3, len(templates))
        self.assertEqual(
            {"idor", "sql_injection", "stored_xss"},
            {item["vulnerability_class"] for item in templates},
        )
        self.assertTrue(all(item["synthetic_data_only"] for item in templates))
        self.assertTrue(
            all(not any(item["safety"].values()) for item in templates)
        )

    def test_answer_keys_are_not_copied_into_public_static_assets(self) -> None:
        dockerfile = self.dockerfile
        self.assertNotIn("COPY variants", dockerfile)
        static = "\n".join(
            path.read_text(encoding="utf-8") for path in (APP / "static").glob("*")
        )
        for marker in ("lesson-idor", "lesson-sqli", "lesson-stored-xss"):
            self.assertNotIn(marker, static)


if __name__ == "__main__":
    unittest.main()
