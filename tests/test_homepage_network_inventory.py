from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "docker" / "homepage"


class HomepageNetworkInventoryTests(unittest.TestCase):
    def test_network_inventory_card_links_to_live_service(self):
        services = (HOMEPAGE / "config" / "services.yaml").read_text(
            encoding="utf-8"
        )
        card = services.split("    - Network Inventory:", 1)[1].split(
            "    - Loki:", 1
        )[0]
        self.assertIn("href: http://192.168.1.23:3000/#network-topology", card)
        self.assertIn("siteMonitor: http://192.168.1.23:8030/api/v1/health", card)
        self.assertNotIn("target: _blank", card)

    def test_card_target_opens_the_embedded_topology(self):
        custom = (HOMEPAGE / "config" / "custom.js").read_text(encoding="utf-8")
        self.assertIn('topology.id = "network-topology"', custom)
        self.assertIn('window.location.hash === "#network-topology"', custom)
        self.assertIn("topology.open = true", custom)

    def test_card_is_part_of_topology_minor_release(self):
        version = (HOMEPAGE / "version.env").read_text(encoding="utf-8")
        self.assertIn("HOMEPAGE_VAR_DASHBOARD_VERSION=0.11.1", version)


if __name__ == "__main__":
    unittest.main()
