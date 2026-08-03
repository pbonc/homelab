from __future__ import annotations

import importlib.util
import ipaddress
import json
import random
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "quiz_scenario.py"
SPEC = importlib.util.spec_from_file_location("quiz_scenario", SCRIPT)
assert SPEC and SPEC.loader
quiz_scenario = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quiz_scenario)


class QuizScenarioTests(unittest.TestCase):
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

    def test_allocator_fails_closed_when_pool_is_excluded(self) -> None:
        with self.assertRaisesRegex(ValueError, "no non-overlapping"):
            quiz_scenario.allocate_subnet(
                random.Random(1), [ipaddress.ip_network("172.29.0.0/16")]
            )

    def test_decoy_count_is_bounded(self) -> None:
        for value in (2, 9):
            with self.assertRaisesRegex(ValueError, "between 3 and 8"):
                quiz_scenario.generate_scenario(1, decoy_count=value)


if __name__ == "__main__":
    unittest.main()
