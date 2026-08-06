from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "docker" / "purple-range-portal"


class PurpleRangePortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (PORTAL / "compose.yaml").read_text(encoding="utf-8")
        cls.server = (PORTAL / "purple_range_portal" / "__main__.py").read_text(
            encoding="utf-8"
        )
        cls.index = (PORTAL / "static" / "index.html").read_text(encoding="utf-8")
        cls.script = (PORTAL / "static" / "app.js").read_text(encoding="utf-8")

    def test_service_is_lan_bound_read_only_and_constrained(self) -> None:
        self.assertIn('"192.168.1.23:8050:8050"', self.compose)
        self.assertIn("read_only: true", self.compose)
        self.assertIn("cap_drop:", self.compose)
        self.assertIn("no-new-privileges:true", self.compose)
        self.assertIn("/api/health", self.compose)
        self.assertNotIn("docker.sock", self.compose)
        self.assertNotIn("privileged: true", self.compose)

    def test_page_explains_both_launch_steps(self) -> None:
        self.assertIn("make purple-range-up", self.index)
        self.assertIn("3008:127.0.0.1:3008", self.index)
        self.assertIn("id_ed25519_homelab", self.index)
        self.assertIn('href="http://127.0.0.1:3008"', self.index)
        self.assertIn("make purple-range-reset", self.index)

    def test_target_link_requires_browser_local_probe(self) -> None:
        self.assertIn("JuiceShop_Logo.png", self.script)
        self.assertIn('launch.setAttribute("aria-disabled"', self.script)
        self.assertIn("event.preventDefault()", self.script)
        self.assertIn("setConnection(true)", self.script)

    def test_copy_buttons_support_plain_http_lan_browsers(self) -> None:
        self.assertIn("navigator.clipboard?.writeText", self.script)
        self.assertIn('document.execCommand("copy")', self.script)

    def test_server_exposes_no_range_control_or_docker_api(self) -> None:
        self.assertIn('path == "/api/health"', self.server)
        self.assertNotIn("subprocess", self.server)
        self.assertNotIn("docker", self.server.lower())
        self.assertNotIn("do_POST", self.server)


if __name__ == "__main__":
    unittest.main()
