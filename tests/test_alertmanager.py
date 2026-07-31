from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY = ROOT / "docker" / "observability"


class AlertmanagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose = (OBSERVABILITY / "compose.yaml").read_text(encoding="utf-8")
        cls.prometheus = (OBSERVABILITY / "prometheus.yml").read_text(
            encoding="utf-8"
        )
        cls.alertmanager = (OBSERVABILITY / "alertmanager.yml").read_text(
            encoding="utf-8"
        )

    def test_alertmanager_is_pinned_and_lan_only(self) -> None:
        self.assertRegex(
            self.compose,
            r"quay\.io/prometheus/alertmanager@sha256:[0-9a-f]{64}",
        )
        self.assertIn('"192.168.1.23:9093:9093"', self.compose)
        self.assertIn("mem_limit: 192m", self.compose)
        self.assertIn("pids_limit: 128", self.compose)

    def test_prometheus_routes_alerts_and_scrapes_alertmanager(self) -> None:
        self.assertIn("alerting:", self.prometheus)
        self.assertIn("alertmanager:9093", self.prometheus)
        self.assertIn("job_name: alertmanager", self.prometheus)

    def test_ntfy_receiver_uses_password_file_and_resolutions(self) -> None:
        self.assertIn("?template=alertmanager", self.alertmanager)
        self.assertIn("username: homelab-publisher", self.alertmanager)
        self.assertIn(
            "password_file: /run/secrets/ntfy_publisher_password",
            self.alertmanager,
        )
        self.assertIn("send_resolved: true", self.alertmanager)
        self.assertNotIn("publisher_password.txt", self.alertmanager)

    def test_grouping_repetition_and_inhibition_are_conservative(self) -> None:
        for setting in (
            "group_wait: 30s",
            "group_interval: 5m",
            "repeat_interval: 4h",
            'alertname="BrainRootDiskCritical"',
            'alertname="BrainRootDiskHigh"',
        ):
            self.assertIn(setting, self.alertmanager)

    def test_synthetic_test_is_bounded_and_resolves(self) -> None:
        script = (ROOT / "scripts" / "alertmanager_test.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("HomelabNotificationTest", script)
        self.assertIn('"endsAt"', script)
        self.assertNotIn("systemctl stop", script)
        self.assertNotIn("docker stop", script)

    def test_hardware_outage_requires_ten_continuous_minutes(self) -> None:
        rules = (OBSERVABILITY / "rules" / "homelab.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("alert: HardwareNodeUnavailable", rules)
        self.assertIn('up{job=~"node|piaware-node"} == 0', rules)
        hardware = rules.split("alert: HardwareNodeUnavailable", 1)[1]
        self.assertIn("for: 10m", hardware.split("- alert:", 1)[0])
        generic = rules.split("alert: PrometheusTargetDown", 1)[1]
        self.assertIn('up{job!~"node|piaware-node"} == 0', generic)


if __name__ == "__main__":
    unittest.main()
