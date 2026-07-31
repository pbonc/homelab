from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NTFY = ROOT / "docker" / "ntfy"


class NtfyDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose_text = (NTFY / "compose.yaml").read_text(encoding="utf-8")
        cls.config_text = (NTFY / "server.yml").read_text(encoding="utf-8")

    def test_image_is_digest_pinned_and_version_documented(self) -> None:
        self.assertRegex(
            self.compose_text,
            r"image: binwiederhier/ntfy@sha256:[0-9a-f]{64} # v2\.26\.3",
        )
        self.assertIn("# v2.26.3", self.compose_text)

    def test_service_is_bound_only_to_brain_lan_address(self) -> None:
        self.assertIn('"192.168.1.23:8093:80"', self.compose_text)
        self.assertNotIn("0.0.0.0", self.compose_text)

    def test_private_access_is_declarative_and_least_privilege(self) -> None:
        self.assertIn('auth-default-access: "deny-all"', self.config_text)
        self.assertIn("enable-signup: false", self.config_text)
        self.assertIn("NTFY_AUTH_USERS:", self.compose_text)
        self.assertIn("NTFY_AUTH_ACCESS:", self.compose_text)
        example = (NTFY / ".env.example").read_text(encoding="utf-8")
        self.assertIn("homelab-publisher:homelab-alerts:wo", example)
        self.assertIn("homelab-iphone:homelab-alerts:ro", example)

    def test_state_retention_health_and_limits_are_explicit(self) -> None:
        self.assertIn('cache-duration: "7d"', self.config_text)
        self.assertIn('cache-file: "/var/lib/ntfy/cache.db"', self.config_text)
        self.assertIn('auth-file: "/var/lib/ntfy/user.db"', self.config_text)
        self.assertIn("ntfy-data:/var/lib/ntfy", self.compose_text)
        self.assertIn("healthcheck:", self.compose_text)
        self.assertIn("mem_limit: 192m", self.compose_text)
        self.assertIn("cpus: 0.50", self.compose_text)
        self.assertIn("pids_limit: 128", self.compose_text)

    def test_ios_upstream_and_local_base_url_are_explicit(self) -> None:
        self.assertIn('base-url: "http://192.168.1.23:8093"', self.config_text)
        self.assertIn('upstream-base-url: "https://ntfy.sh"', self.config_text)

    def test_runtime_credentials_are_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("docker/ntfy/.env", ignore)
        self.assertIn("docker/ntfy/secrets/", ignore)
        self.assertFalse((NTFY / ".env.example").read_text().count("tk_"))

    def test_password_hash_parser_accepts_bcrypt_only(self) -> None:
        source = (ROOT / "scripts" / "ntfy_secrets.py").read_text(encoding="utf-8")
        self.assertIn("HASH_PATTERN", source)
        self.assertIn(r"\$2[aby]\$", source)
        self.assertIn('replace("$", "$$")', source)
        self.assertIn("pty.openpty()", source)
        self.assertIn('"--tty"', source)
        self.assertIn("mode=0o644", source)


if __name__ == "__main__":
    unittest.main()
