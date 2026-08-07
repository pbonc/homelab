from __future__ import annotations

import importlib.util
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
quiz_range_lifecycle = load_script("quiz_range_lifecycle")


class QuizRangeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = quiz_scenario.generate_scenario(42, decoy_count=5)

    def test_expected_surface_contains_only_manifest_services(self) -> None:
        surface = quiz_range_lifecycle.expected_surface(self.scenario)
        self.assertEqual(6, len(surface))
        self.assertIn((self.scenario["target"]["address"], 8080), surface)
        self.assertNotIn(("192.168.1.23", 3000), surface)

    def test_nmap_xml_parser_returns_only_open_tcp_surface(self) -> None:
        payload = """<?xml version='1.0'?>
        <nmaprun><host><address addr='172.29.1.5'/><ports>
        <port protocol='tcp' portid='8080'><state state='open'/></port>
        <port protocol='tcp' portid='8090'><state state='closed'/></port>
        </ports></host></nmaprun>"""
        self.assertEqual(
            {("172.29.1.5", 8080)}, quiz_range_lifecycle.parse_nmap_xml(payload)
        )

    def test_invalid_scan_output_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "invalid nmap XML"):
            quiz_range_lifecycle.parse_nmap_xml("not XML")

    def test_private_loader_requires_both_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "not prepared"):
                quiz_range_lifecycle.load_private(Path(directory))

    def test_compose_command_uses_explicit_private_model(self) -> None:
        command = quiz_range_lifecycle.compose_command(
            Path(".runtime/quiz-range/compose.json"), "up", "--detach", "--wait"
        )
        self.assertEqual("docker", command[0])
        self.assertEqual(Path(".runtime/quiz-range/compose.json"), Path(command[3]))
        self.assertEqual(["up", "--detach", "--wait"], command[4:])

    def test_toolbox_builds_are_explicit_and_bounded(self) -> None:
        self.assertEqual(3, len(quiz_range_lifecycle.IMAGE_BUILDS))
        contexts = {context for _, context in quiz_range_lifecycle.IMAGE_BUILDS}
        self.assertEqual(
            {
                Path("docker/trailhead-rentals"),
                Path("docker/quiz-decoy"),
                Path("docker/quiz-attacker"),
            },
            contexts,
        )


if __name__ == "__main__":
    unittest.main()
