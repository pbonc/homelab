from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomepagePiAwareTests(unittest.TestCase):
    def test_piaware_uses_one_custom_health_source(self):
        services = (
            ROOT / "docker" / "homepage" / "config" / "services.yaml"
        ).read_text(encoding="utf-8")
        piaware = services.split("    - piaware:", 1)[1].split(
            "\n- Deployed Services:",
            1,
        )[0]
        self.assertNotIn("siteMonitor:", piaware)
        self.assertNotIn("widget:", piaware)
        self.assertNotIn("widgets:", piaware)

        custom = (
            ROOT / "docker" / "homepage" / "config" / "custom.js"
        ).read_text(encoding="utf-8")
        self.assertIn("async function refreshPiaware()", custom)
        self.assertIn("http://192.168.1.23:9090/api/v1/query", custom)
        self.assertIn("piaware_aircraft_visible", custom)
        self.assertIn("piaware_feed_report_age_seconds", custom)
        self.assertIn("piaware_reception_range_max_nautical_miles", custom)
        self.assertIn("node_cpu_seconds_total", custom)
        self.assertIn("node_memory_MemAvailable_bytes", custom)
        self.assertIn("node_uname_info", custom)
        self.assertIn("piaware-hardware", custom)
        self.assertIn("renderPiawareMetrics(card, values)", custom)

    def test_piaware_reuses_brain_health_states_and_badge(self):
        custom = (
            ROOT / "docker" / "homepage" / "config" / "custom.js"
        ).read_text(encoding="utf-8")
        self.assertIn('serviceCard("piaware")', custom)
        self.assertIn("async function refreshPiaware()", custom)
        self.assertIn('setBadge(card, "active", "Active")', custom)
        self.assertIn('setBadge(card, "warning"', custom)
        self.assertIn('setBadge(card, "critical"', custom)
        self.assertIn('setBadge(card, "unavailable", "Unavailable")', custom)
        self.assertIn("refreshPiaware();", custom)

    def test_brain_and_piaware_metric_panels_share_fixed_height(self):
        css = (
            ROOT / "docker" / "homepage" / "config" / "custom.css"
        ).read_text(encoding="utf-8")
        brain = css.split(
            ".services-group:nth-child(1) .service-card .service-container {", 1
        )[1].split("}", 1)[0]
        hardware = css.split(".piaware-hardware {", 1)[1].split("}", 1)[0]
        metrics = css.split(".piaware-metrics {", 1)[1].split("}", 1)[0]
        for panel in (brain, hardware, metrics):
            self.assertIn("box-sizing: border-box;", panel)
            self.assertIn("height: 4rem;", panel)


if __name__ == "__main__":
    unittest.main()
