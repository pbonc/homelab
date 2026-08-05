from __future__ import annotations

import importlib.util
import ipaddress
import json
import random
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "quiz_scenario.py"
SPEC = importlib.util.spec_from_file_location("quiz_scenario", SCRIPT)
assert SPEC and SPEC.loader
quiz_scenario = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quiz_scenario)


class QuizScenarioTests(unittest.TestCase):
    @staticmethod
    def docker_result(
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, stdout, stderr)

    def test_same_seed_produces_same_scenario(self) -> None:
        first = quiz_scenario.generate_scenario(42)
        second = quiz_scenario.generate_scenario(42)
        self.assertEqual(first, second)

    def test_different_seeds_change_scenario(self) -> None:
        self.assertNotEqual(
            quiz_scenario.generate_scenario(1),
            quiz_scenario.generate_scenario(2),
        )

    def test_allocator_never_overlaps_excluded_networks(self) -> None:
        excluded = quiz_scenario.parse_networks(
            ["172.29.0.0/20", "192.168.1.0/24", "172.24.0.0/16"]
        )
        for seed in range(100):
            scenario = quiz_scenario.generate_scenario(seed, excluded)
            subnet = ipaddress.ip_network(scenario["authorized_cidr"])
            self.assertEqual(27, subnet.prefixlen)
            self.assertTrue(all(not subnet.overlaps(item) for item in excluded))

    def test_target_and_decoys_stay_inside_scope_and_are_unique(self) -> None:
        scenario = quiz_scenario.generate_scenario(101, decoy_count=8)
        subnet = ipaddress.ip_network(scenario["authorized_cidr"])
        addresses = [scenario["target"]["address"], *scenario["decoys"]]
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertTrue(all(ipaddress.ip_address(item) in subnet for item in addresses))

    def test_scenario_is_silent_by_contract(self) -> None:
        scenario = quiz_scenario.generate_scenario(55)
        self.assertEqual("never", scenario["notification_policy"])

    def test_schema_and_generator_catalog_match(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "vulnerability-quiz-scenario-v1.json").read_text(
                encoding="utf-8"
            )
        )
        enum = schema["properties"]["target"]["properties"]["quiz_type"]["enum"]
        self.assertEqual(sorted(quiz_scenario.QUIZ_TYPES), sorted(enum))
        template_enum = schema["properties"]["target"]["properties"]["template_id"][
            "enum"
        ]
        self.assertEqual(
            sorted(quiz_scenario.QUIZ_TEMPLATES.values()), sorted(template_enum)
        )

    def test_answer_key_maps_class_to_named_template(self) -> None:
        for seed in range(30):
            target = quiz_scenario.generate_scenario(seed)["target"]
            self.assertEqual(
                quiz_scenario.QUIZ_TEMPLATES[target["quiz_type"]],
                target["template_id"],
            )

    def test_answer_key_selects_one_to_three_compatible_trailhead_variants(self) -> None:
        observed_counts = set()
        for seed in range(100):
            target = quiz_scenario.generate_scenario(seed)["target"]
            classes = tuple(target["vulnerability_classes"])
            observed_counts.add(len(classes))
            self.assertEqual(
                [quiz_scenario.QUIZ_TEMPLATES[item] for item in classes],
                target["template_ids"],
            )
            self.assertEqual(
                quiz_scenario.TRAILHEAD_VARIANT_SETS[classes],
                target["trailhead_variant_set"],
            )
        self.assertEqual({1, 2, 3}, observed_counts)

    def test_allocator_fails_closed_when_pool_is_excluded(self) -> None:
        with self.assertRaisesRegex(ValueError, "no non-overlapping"):
            quiz_scenario.allocate_subnet(
                random.Random(1), [ipaddress.ip_network("172.29.0.0/16")]
            )

    def test_live_docker_subnets_are_discovered(self) -> None:
        responses = iter(
            [
                self.docker_result(stdout="network-a\nnetwork-b\n"),
                self.docker_result(
                    stdout=json.dumps(
                        [
                            {"IPAM": {"Config": [{"Subnet": "172.24.0.0/16"}]}},
                            {
                                "IPAM": {
                                    "Config": [
                                        {"Subnet": "172.29.4.1/24"},
                                        {"Subnet": "fd00::/64"},
                                    ]
                                }
                            },
                        ]
                    )
                ),
            ]
        )

        discovered = quiz_scenario.discover_docker_networks(
            lambda *args, **kwargs: next(responses)
        )

        self.assertEqual(
            [
                ipaddress.ip_network("172.24.0.0/16"),
                ipaddress.ip_network("172.29.4.0/24"),
            ],
            discovered,
        )

    def test_live_docker_discovery_fails_closed_on_list_error(self) -> None:
        with self.assertRaisesRegex(
            quiz_scenario.DockerNetworkDiscoveryError, "no scenario was generated"
        ):
            quiz_scenario.discover_docker_networks(
                lambda *args, **kwargs: self.docker_result(
                    returncode=1, stderr="permission denied"
                )
            )

    def test_live_docker_discovery_fails_closed_on_partial_inspection(self) -> None:
        responses = iter(
            [
                self.docker_result(stdout="network-a\nnetwork-b\n"),
                self.docker_result(stdout=json.dumps([{"IPAM": {"Config": []}}])),
            ]
        )
        with self.assertRaisesRegex(
            quiz_scenario.DockerNetworkDiscoveryError,
            "every requested network",
        ):
            quiz_scenario.discover_docker_networks(
                lambda *args, **kwargs: next(responses)
            )

    def test_live_docker_discovery_fails_closed_if_inspection_cannot_start(self) -> None:
        calls = 0

        def run(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return self.docker_result(stdout="network-a\n")
            raise FileNotFoundError("docker disappeared")

        with self.assertRaisesRegex(
            quiz_scenario.DockerNetworkDiscoveryError,
            "cannot inspect Docker networks",
        ):
            quiz_scenario.discover_docker_networks(run)

    def test_live_docker_discovery_fails_closed_on_invalid_subnet(self) -> None:
        responses = iter(
            [
                self.docker_result(stdout="network-a\n"),
                self.docker_result(
                    stdout=json.dumps(
                        [{"IPAM": {"Config": [{"Subnet": "not-a-network"}]}}]
                    )
                ),
            ]
        )
        with self.assertRaisesRegex(
            quiz_scenario.DockerNetworkDiscoveryError, "invalid network subnet"
        ):
            quiz_scenario.discover_docker_networks(
                lambda *args, **kwargs: next(responses)
            )

    def test_decoy_count_is_bounded(self) -> None:
        for value in (2, 9):
            with self.assertRaisesRegex(ValueError, "between 3 and 8"):
                quiz_scenario.generate_scenario(1, decoy_count=value)


if __name__ == "__main__":
    unittest.main()
