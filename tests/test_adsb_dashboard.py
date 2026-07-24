import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "docker" / "telemetry" / "grafana" / "dashboards" / "adsb.json"


class AdsbDashboardTests(unittest.TestCase):
    def test_dashboard_uses_aggregate_prometheus_metrics(self):
        dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        self.assertEqual(dashboard["uid"], "homelab-adsb")
        self.assertEqual(dashboard["title"], "ADS-B Receiver")
        self.assertFalse(dashboard["editable"])
        self.assertEqual(dashboard["annotations"], {"list": []})
        breakdowns = {
            panel["title"]: panel
            for panel in dashboard["panels"]
            if panel["title"] in {
                "Registration Countries (Current)",
                "Inferred Operators (Current)",
            }
        }
        self.assertEqual(len(breakdowns), 2)
        for panel in breakdowns.values():
            self.assertGreaterEqual(panel["gridPos"]["w"], 8)
            self.assertEqual(panel["type"], "bargauge")
            self.assertEqual(panel["options"]["orientation"], "vertical")
            self.assertEqual(panel["options"]["namePlacement"], "bottom")
            self.assertEqual(panel["options"]["sizing"], "manual")
            self.assertIn("sort_desc(", panel["targets"][0]["expr"])

        encoded = json.dumps(dashboard).lower()
        for metric in (
            "piaware_aircraft_visible",
            "piaware_aircraft_seen_60_seconds",
            "piaware_feed_report_age_seconds",
            "piaware_messages_total",
            "piaware_sdr_present",
            "piaware_service_up",
            "node_cpu_seconds_total",
            "node_memory_memavailable_bytes",
            "node_filesystem_avail_bytes",
            "max_over_time",
            "avg_over_time",
            "piaware_aircraft_by_registration_country",
            "piaware_aircraft_by_operator",
            "piaware_reception_range_max_nautical_miles",
            "piaware_reception_range_p95_nautical_miles",
            "piaware_reception_range_median_nautical_miles",
            "piaware_positioned_aircraft",
        ):
            self.assertIn(metric, encoded)

        for forbidden in (
            "feeder_id",
            "callsign",
            "latitude",
            "longitude",
            "aircraft_hex",
            "deployment_event",
        ):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
