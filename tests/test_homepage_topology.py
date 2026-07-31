from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "docker" / "homepage"


class HomepageTopologyTests(unittest.TestCase):
    def test_topology_panel_uses_versioned_read_only_api(self):
        custom = (HOMEPAGE / "config" / "custom.js").read_text(encoding="utf-8")
        self.assertIn("http://192.168.1.23:8030/api/v1/topology", custom)
        self.assertIn('payload.schema_version !== "1.0.0"', custom)
        self.assertIn('fetch(TOPOLOGY_URL, { cache: "no-store" })', custom)
        self.assertNotIn('method: "POST"', custom)

    def test_panel_is_collapsible_bounded_and_accessible(self):
        custom = (HOMEPAGE / "config" / "custom.js").read_text(encoding="utf-8")
        css = (HOMEPAGE / "config" / "custom.css").read_text(encoding="utf-8")
        self.assertIn('document.createElement("details")', custom)
        self.assertIn("network-topology-full", custom)
        self.assertIn("tabIndex = 0", custom)
        self.assertIn("max-height: 22rem", css)
        self.assertIn(":focus-visible", css)

    def test_renderer_names_shared_lan_without_inventing_links(self):
        custom = (HOMEPAGE / "config" / "custom.js").read_text(encoding="utf-8")
        self.assertIn("Observed membership on the shared trusted LAN", custom)
        self.assertIn("Trusted LAN", custom)
        self.assertNotIn("switch port", custom.lower())

    def test_topology_release_is_a_minor_dashboard_version(self):
        version = (HOMEPAGE / "version.env").read_text(encoding="utf-8")
        self.assertIn("HOMEPAGE_VAR_DASHBOARD_VERSION=0.11.4", version)


if __name__ == "__main__":
    unittest.main()
