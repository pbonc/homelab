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
