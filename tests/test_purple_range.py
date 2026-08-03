import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANGE = ROOT / "docker" / "purple-range"


class PurpleRangePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (RANGE / "compose.yaml").read_text(encoding="utf-8")
        cls.docs = (ROOT / "docs" / "purple-range.md").read_text(encoding="utf-8")
        cls.verify = (ROOT / "scripts" / "purple_range_verify.sh").read_text(
            encoding="utf-8"
        )

    def test_images_are_digest_pinned(self) -> None:
        images = re.findall(r"^\s+image:\s+(\S+)", self.compose, re.MULTILINE)
        self.assertEqual(3, len(images))
        for image in images:
            self.assertRegex(image, r"^[^@]+@sha256:[0-9a-f]{64}$")

    def test_target_is_loopback_only(self) -> None:
        self.assertIn('"127.0.0.1:3008:8080"', self.compose)
        self.assertNotIn("0.0.0.0", self.compose)
        self.assertNotIn('"192.168.1.23:3008:8080"', self.compose)

    def test_range_network_is_internal_and_standalone(self) -> None:
        self.assertIn("internal: true", self.compose)
        self.assertNotIn("external: true", self.compose)
        self.assertEqual(3, self.compose.count("- target-range"))
        self.assertEqual(1, self.compose.count("- range-ingress"))

    def test_attacker_is_explicit_disposable_profile(self) -> None:
        attacker = self.compose.split("  attacker:", 1)[1]
        self.assertIn("profiles:", attacker)
        self.assertIn("- attacker", attacker)
        self.assertIn('restart: "no"', attacker)
        self.assertIn("read_only: true", attacker)

    def test_services_drop_capabilities_and_are_bounded(self) -> None:
        self.assertEqual(3, self.compose.count("cap_drop:"))
        self.assertEqual(3, self.compose.count("no-new-privileges:true"))
        self.assertEqual(3, self.compose.count("mem_limit:"))
        self.assertEqual(3, self.compose.count("pids_limit:"))

    def test_no_sensitive_mounts_or_privileged_modes(self) -> None:
        forbidden = ("privileged: true", "/var/run/docker.sock", "/srv/", "secrets:")
        for value in forbidden:
            self.assertNotIn(value, self.compose)

    def test_verifier_has_positive_and_negative_assertions(self) -> None:
        self.assertIn("http://juice-shop:3000/", self.verify)
        self.assertIn("http://127.0.0.1:3008/", self.verify)
        self.assertIn("http://192.168.1.23:3000/", self.verify)
        self.assertIn("http://1.1.1.1/", self.verify)
        self.assertIn("[FAIL] Attacker reached a production service", self.verify)
        self.assertIn("[FAIL] Attacker reached the internet", self.verify)

    def test_authorization_boundary_is_explicit(self) -> None:
        self.assertIn("Authorization covers only", self.docs)
        self.assertIn("It does not cover `brain`, `piaware`", self.docs)
        self.assertIn("Never add host networking", self.docs)


if __name__ == "__main__":
    unittest.main()
