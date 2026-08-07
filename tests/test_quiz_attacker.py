from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATTACKER = ROOT / "docker" / "quiz-attacker"


class QuizAttackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dockerfile = (ATTACKER / "Dockerfile").read_text(encoding="utf-8")
        cls.compose = (ATTACKER / "compose.yaml").read_text(encoding="utf-8")

    def test_base_is_digest_pinned_and_tools_are_baked_in(self) -> None:
        self.assertRegex(self.dockerfile, r"FROM .+@sha256:[0-9a-f]{64}")
        self.assertIn("apk add --no-cache bind-tools nmap", self.dockerfile)
        self.assertIn("USER curl_user", self.dockerfile)

    def test_standalone_attacker_is_off_by_default_and_disposable(self) -> None:
        for expected in (
            "profiles:",
            "- attacker",
            "read_only: true",
            "cap_drop:",
            "no-new-privileges:true",
            'restart: "no"',
            "internal: true",
            "notification_policy: never",
        ):
            self.assertIn(expected, self.compose)
        self.assertNotIn("ports:", self.compose)
        self.assertNotIn("privileged: true", self.compose)
        self.assertNotIn("/var/run/docker.sock", self.compose)


if __name__ == "__main__":
    unittest.main()

