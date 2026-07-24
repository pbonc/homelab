from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomepagePiAwareTests(unittest.TestCase):
    def test_piaware_uses_compact_prometheus_metrics(self):
        services = (
            ROOT / "docker" / "homepage" / "config" / "services.yaml"
        ).read_text(encoding="utf-8")
        piaware = services.split("    - piaware:", 1)[1].split(
            "\n- Deployed Services:",
            1,
        )[0]
        self.assertIn("\n        widget:\n", piaware)
        self.assertNotIn("\n        widgets:\n", piaware)
        self.assertIn("type: prometheusmetric", piaware)
        self.assertIn("url: http://192.168.1.23:9090", piaware)
        self.assertIn('piaware_aircraft_visible{instance="piaware"}', piaware)
        self.assertIn('piaware_feed_report_age_seconds{instance="piaware"}', piaware)
        self.assertIn(
            'piaware_reception_range_max_nautical_miles{instance="piaware"}',
            piaware,
        )
        self.assertEqual(piaware.count("- label:"), 3)

    def test_piaware_reuses_brain_health_states_and_badge(self):
        custom = (
            ROOT / "docker" / "homepage" / "config" / "custom.js"
        ).read_text(encoding="utf-8")
        self.assertIn('serviceCard("piaware")', custom)
        self.assertIn("function updatePiawareHealth()", custom)
        self.assertIn('setBadge(card, "active", "Active")', custom)
        self.assertIn('setBadge(card, "warning"', custom)
        self.assertIn('setBadge(card, "critical"', custom)
        self.assertIn('setBadge(card, "unavailable", "Unavailable")', custom)
        self.assertIn("updatePiawareHealth();", custom)


if __name__ == "__main__":
    unittest.main()
