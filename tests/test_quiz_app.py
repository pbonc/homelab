from __future__ import annotations

import http.client
import importlib.util
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "docker" / "quiz-app"
sys.path.insert(0, str(APP))

from quiz_app.authorization import find_expense  # noqa: E402
from quiz_app.server import QuizHandler, ThreadingHTTPServer  # noqa: E402


class ExpensePortalUnitTests(unittest.TestCase):
    def test_vulnerable_mode_omits_object_ownership_check(self) -> None:
        expense = find_expense("alex", 1042, "vulnerable")
        self.assertIsNotNone(expense)
        self.assertEqual("sam", expense.owner)

    def test_fixed_mode_enforces_object_ownership(self) -> None:
        self.assertIsNone(find_expense("alex", 1042, "fixed"))
        self.assertIsNotNone(find_expense("alex", 1041, "fixed"))

    def test_unknown_mode_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "vulnerable or fixed"):
            find_expense("alex", 1041, "mystery")


class ExpensePortalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuizHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def login_cookie(self) -> str:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = urlencode({"username": "alex", "password": "training-only-41"})
        connection.request(
            "POST",
            "/login",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        response.read()
        self.assertEqual(303, response.status)
        cookie = response.getheader("Set-Cookie")
        connection.close()
        assert cookie
        return cookie.split(";", 1)[0]

    def get_expense(self, expense_id: int, cookie: str) -> tuple[int, dict[str, object]]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(
            "GET", f"/api/expenses/{expense_id}", headers={"Cookie": cookie}
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        status = response.status
        connection.close()
        return status, payload

    def test_http_vulnerable_and_fixed_modes_have_opposite_behavior(self) -> None:
        cookie = self.login_cookie()
        with patch.dict(os.environ, {"QUIZ_MODE": "vulnerable"}):
            status, payload = self.get_expense(1042, cookie)
            self.assertEqual(200, status)
            self.assertEqual("Northwind Hotel", payload["merchant"])
            self.assertNotIn("owner", payload)

        with patch.dict(os.environ, {"QUIZ_MODE": "fixed"}):
            status, payload = self.get_expense(1042, cookie)
            self.assertEqual(404, status)
            self.assertEqual({"error": "not_found"}, payload)

    def test_api_requires_authentication(self) -> None:
        status, payload = self.get_expense(1041, "")
        self.assertEqual(401, status)
        self.assertEqual({"error": "authentication_required"}, payload)


class QuizTemplateContractTests(unittest.TestCase):
    def test_template_is_bounded_and_synthetic(self) -> None:
        template = json.loads(
            (APP / "templates" / "expense-idor.json").read_text(encoding="utf-8")
        )
        self.assertEqual("1.0.0", template["schema_version"])
        self.assertEqual("idor", template["vulnerability_class"])
        self.assertEqual(["vulnerable", "fixed"], template["modes"])
        self.assertTrue(template["synthetic_data_only"])
        self.assertTrue(all(value is False for value in template["safety"].values()))

    def test_schema_requires_answer_and_safety_fields(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "vulnerability-quiz-template-v1.json").read_text(
                encoding="utf-8"
            )
        )
        for field in ("success_evidence", "root_cause", "mitigation", "safety"):
            self.assertIn(field, schema["required"])

    def test_compose_is_internal_silent_and_constrained(self) -> None:
        compose = (APP / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("internal: true", compose)
        self.assertIn("notification_policy: never", compose)
        self.assertIn("expected_vulnerable:", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("cap_drop:", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("privileged: true", compose)
        self.assertNotIn("/var/run/docker.sock", compose)

    def test_source_has_no_process_file_upload_or_http_client_capability(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (APP / "quiz_app").glob("*.py")
        )
        for forbidden in ("subprocess", "os.system", "cgi.FieldStorage", "requests."):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
