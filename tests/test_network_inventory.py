from __future__ import annotations

import json
import sys
import tempfile
import unittest
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "docker" / "network-inventory"
sys.path.insert(0, str(SERVICE_ROOT))

from network_inventory.config import KnownInventory, is_private_mac  # noqa: E402
from network_inventory.notifier import publish_unknown_device  # noqa: E402
from network_inventory.scanner import parse_arp_table, parse_nmap_xml, scan  # noqa: E402
from network_inventory.store import InventoryStore, Observation  # noqa: E402


def known_file(directory: str) -> Path:
    path = Path(directory) / "known.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "devices": [
                    {
                        "id": "host-brain",
                        "name": "brain",
                        "kind": "controller",
                        "address": "192.168.1.23",
                        "mac": "02:00:00:00:00:23",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class NetworkInventoryTests(unittest.TestCase):
    def make_store(self, directory: str) -> InventoryStore:
        return InventoryStore(
            Path(directory) / "inventory.db",
            KnownInventory(known_file(directory)),
            confirmation_seconds=300,
            private_confirmation_seconds=1800,
            offline_seconds=300,
            stale_seconds=300,
        )

    def test_known_inventory_rejects_duplicate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = known_file(directory)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["devices"].append(payload["devices"][0])
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                KnownInventory(path)

    def test_api_allows_both_trusted_homepage_origins(self) -> None:
        main = (
            SERVICE_ROOT / "network_inventory" / "main.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"http://192.168.1.23:3000"', main)
        self.assertIn('"http://brain:3000"', main)
        self.assertIn("origin in HOMEPAGE_ORIGINS", main)

    def test_unknown_device_requires_two_separated_scans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            store.record_scan(
                [Observation("02:00:00:00:00:23", "192.168.1.23")],
                completed_at=start,
            )
            unknown = Observation("00:11:22:33:44:55", "192.168.1.50")
            first = store.record_scan(
                [unknown], completed_at=start + timedelta(seconds=1)
            )
            early = store.record_scan(
                [unknown], completed_at=start + timedelta(minutes=2)
            )
            confirmed = store.record_scan(
                [unknown], completed_at=start + timedelta(minutes=6)
            )
            self.assertEqual(first["newly_confirmed"], 0)
            self.assertEqual(early["newly_confirmed"], 0)
            self.assertEqual(confirmed["newly_confirmed"], 1)
            node = next(
                item
                for item in store.topology(start + timedelta(minutes=6))["nodes"]
                if item["mac"] == "00:11:22:33:44:55"
            )
            self.assertTrue(node["confirmed"])
            self.assertFalse(node["known"])

    def test_private_mac_uses_longer_three_scan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            store.record_scan(
                [Observation("02:00:00:00:00:23", "192.168.1.23")],
                completed_at=start,
            )
            private = Observation("02:11:22:33:44:55", "192.168.1.51")
            self.assertTrue(is_private_mac(private.mac))
            store.record_scan(
                [private], completed_at=start + timedelta(seconds=1)
            )
            store.record_scan(
                [private], completed_at=start + timedelta(minutes=10)
            )
            result = store.record_scan(
                [private], completed_at=start + timedelta(minutes=31)
            )
            self.assertEqual(result["newly_confirmed"], 1)

    def test_pending_notification_is_cleared_only_after_marking_sent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            store.record_scan(
                [Observation("02:00:00:00:00:23", "192.168.1.23")],
                completed_at=start,
            )
            unknown = Observation("00:11:22:33:44:55", "192.168.1.50")
            store.record_scan(
                [unknown], completed_at=start + timedelta(seconds=1)
            )
            store.record_scan(
                [unknown], completed_at=start + timedelta(minutes=6)
            )
            pending = store.pending_notifications()
            self.assertEqual(len(pending), 1)
            store.mark_notification_sent(
                str(pending[0]["mac"]),
                sent_at=start + timedelta(minutes=6, seconds=1),
            )
            self.assertEqual(store.pending_notifications(), [])

    def test_initial_scan_establishes_a_silent_notification_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            existing = Observation("00:11:22:33:44:55", "192.168.1.50")
            store.record_scan([], completed_at=start)
            store.record_scan(
                [existing], completed_at=start + timedelta(minutes=1)
            )
            store.record_scan(
                [existing], completed_at=start + timedelta(minutes=6)
            )
            self.assertEqual(store.pending_notifications(), [])

    def test_ip_change_preserves_stable_node_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            mac = "00:aa:bb:cc:dd:ee"
            store.record_scan(
                [Observation(mac, "192.168.1.70")], completed_at=start
            )
            store.record_scan(
                [Observation(mac, "192.168.1.71")],
                completed_at=start + timedelta(minutes=6),
            )
            topology = store.topology(start + timedelta(minutes=6))
            node = next(item for item in topology["nodes"] if item["mac"] == mac)
            self.assertEqual(
                set(node["addresses"]), {"192.168.1.70", "192.168.1.71"}
            )
            self.assertTrue(str(node["id"]).startswith("device-"))

    def test_topology_uses_shared_segment_and_evidence_backed_edges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            now = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            store.record_scan(
                [Observation("02:00:00:00:00:23", "192.168.1.23")],
                completed_at=now,
            )
            topology = store.topology(now)
            self.assertEqual(topology["schema_version"], "1.0.0")
            self.assertIn(
                "segment-trusted-lan",
                {node["id"] for node in topology["nodes"]},
            )
            self.assertTrue(
                all(
                    edge["kind"] == "membership"
                    and edge["evidence"] in {"declared", "observed"}
                    for edge in topology["edges"]
                )
            )

    def test_health_distinguishes_initializing_stale_and_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            now = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
            self.assertEqual(store.health(now)["status"], "initializing")
            store.record_scan([], completed_at=now)
            self.assertEqual(store.health(now)["status"], "healthy")
            self.assertEqual(
                store.health(now + timedelta(minutes=6))["status"], "stale"
            )
            store.record_scan_failure(
                completed_at=now + timedelta(minutes=7)
            )
            self.assertEqual(
                store.health(now + timedelta(minutes=7))["status"], "failed"
            )

    def test_nmap_parser_ignores_hosts_without_a_mac(self) -> None:
        payload = """<?xml version="1.0"?>
        <nmaprun>
          <host>
            <status state="up"/>
            <address addr="192.168.1.50" addrtype="ipv4"/>
            <address addr="00:11:22:33:44:55" addrtype="mac" vendor="Example"/>
            <hostnames><hostname name="tablet.local"/></hostnames>
          </host>
          <host>
            <status state="up"/>
            <address addr="192.168.1.23" addrtype="ipv4"/>
          </host>
        </nmaprun>"""
        observations = parse_nmap_xml(payload)
        self.assertEqual(
            observations,
            [
                Observation(
                    "00:11:22:33:44:55",
                    "192.168.1.50",
                    "tablet.local",
                    "Example",
                )
            ],
        )

    @patch("network_inventory.scanner.subprocess.run")
    def test_scan_uses_unprivileged_sweep_and_neighbor_table(
        self, run
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            arp_path = Path(directory) / "arp"
            arp_path.write_text(
                "IP address HW type Flags HW address Mask Device\n"
                "192.168.1.27 0x1 0x2 00:11:22:33:44:55 * enp3s0\n",
                encoding="ascii",
            )
            run.return_value.returncode = 0
            run.return_value.stdout = "<nmaprun/>"
            self.assertEqual(
                scan("192.168.1.0/24", arp_path=arp_path),
                [Observation("00:11:22:33:44:55", "192.168.1.27")],
            )
            command = run.call_args.args[0]
            self.assertIn("--unprivileged", command)
            self.assertIn("-sn", command)
            self.assertNotIn("-sS", command)

    @patch("network_inventory.scanner.subprocess.run")
    def test_scan_error_preserves_nmap_diagnostic(self, run) -> None:
        run.return_value.returncode = 1
        run.return_value.stderr = "dnet: Failed to open device eth0"
        with self.assertRaisesRegex(RuntimeError, "Failed to open device eth0"):
            scan("192.168.1.0/24")

    def test_arp_parser_ignores_incomplete_and_out_of_scope_neighbors(self) -> None:
        payload = (
            "IP address HW type Flags HW address Mask Device\n"
            "192.168.1.10 0x1 0x2 00:11:22:33:44:55 * enp3s0\n"
            "192.168.1.11 0x1 0x0 00:00:00:00:00:00 * enp3s0\n"
            "10.0.0.2 0x1 0x2 00:aa:bb:cc:dd:ee * docker0\n"
        )
        self.assertEqual(
            parse_arp_table(payload, "192.168.1.0/24"),
            [Observation("00:11:22:33:44:55", "192.168.1.10")],
        )

    def test_ntfy_publish_uses_basic_auth_and_topic_endpoint(self) -> None:
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

        with tempfile.TemporaryDirectory() as directory:
            password_file = Path(directory) / "password"
            password_file.write_text("correct horse\n", encoding="utf-8")
            with patch(
                "network_inventory.notifier.urllib.request.urlopen",
                return_value=Response(),
            ) as urlopen:
                publish_unknown_device(
                    {
                        "mac": "00:11:22:33:44:55",
                        "node_id": "device-example",
                        "hostname": "tablet",
                        "vendor": "Example",
                        "private_address": False,
                        "first_seen_at": None,
                        "last_seen_at": None,
                    },
                    url="http://192.168.1.23:8093/homelab-alerts",
                    username="homelab-publisher",
                    password_file=password_file,
                )
            request = urlopen.call_args.args[0]
            expected = b64encode(b"homelab-publisher:correct horse").decode("ascii")
            self.assertEqual(request.full_url, "http://192.168.1.23:8093/homelab-alerts")
            self.assertEqual(request.get_header("Authorization"), f"Basic {expected}")
            self.assertIn(b"tablet", request.data)


if __name__ == "__main__":
    unittest.main()
