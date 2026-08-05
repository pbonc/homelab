from __future__ import annotations

import importlib.util
import ipaddress
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quiz_scenario = load_script("quiz_scenario")
quiz_range_compose = load_script("quiz_range_compose")


class QuizRangeComposeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = quiz_scenario.generate_scenario(42, decoy_count=5)
        self.compose = quiz_range_compose.render_compose(self.scenario)

    def test_places_one_target_and_every_decoy_at_manifest_addresses(self) -> None:
        services = self.compose["services"]
        self.assertEqual(6, len(services))
        self.assertEqual(
            self.scenario["target"]["address"],
            services["trailhead-target"]["networks"]["quiz-range"]["ipv4_address"],
        )
        actual_decoys = {
            service["networks"]["quiz-range"]["ipv4_address"]
            for name, service in services.items()
            if name.startswith("decoy-")
        }
        self.assertEqual(
            {item["address"] for item in self.scenario["decoys"]}, actual_decoys
        )

    def test_network_is_internal_and_reserves_gateway(self) -> None:
        network = self.compose["networks"]["quiz-range"]
        subnet = ipaddress.ip_network(self.scenario["authorized_cidr"])
        self.assertTrue(network["internal"])
        self.assertEqual(str(next(subnet.hosts())), network["ipam"]["config"][0]["gateway"])
        self.assertEqual("denied", network["labels"]["homelab.range.internet-access"])

    def test_services_are_silent_constrained_and_have_no_host_ports(self) -> None:
        for service in self.compose["services"].values():
            self.assertEqual("never", service["labels"]["notification_policy"])
            self.assertTrue(service["read_only"])
            self.assertEqual(["ALL"], service["cap_drop"])
            self.assertNotIn("ports", service)
            self.assertNotIn("volumes", service)

    def test_only_target_is_labeled_expected_vulnerable(self) -> None:
        services = self.compose["services"]
        self.assertEqual("true", services["trailhead-target"]["labels"]["expected_vulnerable"])
        self.assertTrue(
            all(
                service["labels"]["expected_vulnerable"] == "false"
                for name, service in services.items()
                if name.startswith("decoy-")
            )
        )

    def test_renderer_rejects_gateway_collision(self) -> None:
        subnet = ipaddress.ip_network(self.scenario["authorized_cidr"])
        self.scenario["target"]["address"] = str(next(subnet.hosts()))
        with self.assertRaisesRegex(ValueError, "usable scenario pool"):
            quiz_range_compose.render_compose(self.scenario)

    def test_private_writer_creates_parent_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "compose.json"
            quiz_range_compose.write_private_json(path, self.compose)
            self.assertTrue(path.is_file())
            self.assertIn('"trailhead-target"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
