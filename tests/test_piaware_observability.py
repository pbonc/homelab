from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible" / "roles" / "piaware_observability"


class PiAwareObservabilityTests(unittest.TestCase):
    def test_playbook_is_restricted_to_piaware(self):
        playbook = (
            ROOT / "ansible" / "playbooks" / "piaware-observability.yml"
        ).read_text(encoding="utf-8")
        tasks = (ROLE / "tasks" / "main.yml").read_text(encoding="utf-8")
        self.assertIn("hosts: piaware", playbook)
        self.assertIn('ansible_facts["hostname"] == "piaware"', tasks)
        self.assertIn('piaware_node_exporter_address != "192.168.1.23"', tasks)

    def test_collector_exports_only_aggregate_receiver_metrics(self):
        collector = (
            ROLE / "templates" / "piaware-export-metrics.py.j2"
        ).read_text(encoding="utf-8")
        compile(collector, "piaware-export-metrics", "exec")
        self.assertNotIn("{{", collector)
        expected = (
            "piaware_feed_report_age_seconds",
            "piaware_aircraft_visible",
            "piaware_aircraft_seen_60_seconds",
            "piaware_messages_total",
            "piaware_sdr_present",
            "piaware_service_up",
            "piaware_metrics_generated_timestamp_seconds",
        )
        for metric in expected:
            self.assertIn(metric, collector)
        self.assertIn("piaware_aircraft_by_registration_country", collector)
        self.assertIn("piaware_aircraft_by_operator", collector)
        for forbidden in ("feeder_id", "latitude", "longitude"):
            self.assertNotIn(forbidden, collector.lower())
        self.assertNotIn("{hex=", collector.lower())
        self.assertNotIn("{flight=", collector.lower())
        self.assertNotIn("{callsign=", collector.lower())

    def test_classifier_uses_local_ranges_and_bounded_operator_groups(self):
        collector = (
            ROLE / "templates" / "piaware-export-metrics.py.j2"
        ).read_text(encoding="utf-8")
        namespace = {"__name__": "classifier_test"}
        exec(compile(collector, "piaware-export-metrics", "exec"), namespace)
        ranges = [
            (0xA00000, 0xAFFFFF, "United States"),
            (0xC00000, 0xC3FFFF, "Canada"),
        ]
        self.assertEqual(
            namespace["registration_country"]("A12345", ranges),
            "United States",
        )
        self.assertEqual(
            namespace["registration_country"]("C01234", ranges),
            "Canada",
        )
        self.assertEqual(namespace["registration_country"]("~ABC123", ranges), "Unknown")
        self.assertEqual(namespace["inferred_operator"]("UAL123 "), "United")
        self.assertEqual(
            namespace["inferred_operator"]("XYZ123"),
            "Unclassified",
        )
        self.assertEqual(namespace["inferred_operator"]("N123AB"), "Unclassified")
        self.assertEqual(namespace["inferred_operator"](None), "Unclassified")

    def test_prometheus_scrapes_the_lan_only_exporter(self):
        prometheus = (
            ROOT / "docker" / "observability" / "prometheus.yml"
        ).read_text(encoding="utf-8")
        defaults = (ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")
        exporter = (
            ROLE / "templates" / "prometheus-node-exporter.default.j2"
        ).read_text(encoding="utf-8")
        self.assertIn("job_name: piaware-node", prometheus)
        self.assertIn("192.168.1.27:9100", prometheus)
        self.assertIn("piaware_node_exporter_port: 9100", defaults)
        self.assertIn("--collector.textfile.directory=", exporter)
        self.assertNotIn("0.0.0.0", exporter)

    def test_timer_refreshes_metrics_without_persisting_missed_runs(self):
        timer = (
            ROLE / "templates" / "piaware-metrics.timer.j2"
        ).read_text(encoding="utf-8")
        self.assertIn("OnUnitActiveSec=15s", timer)
        self.assertIn("Persistent=false", timer)


if __name__ == "__main__":
    unittest.main()
