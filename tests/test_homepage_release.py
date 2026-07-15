from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import homepage_release


class HomepageReleaseTests(unittest.TestCase):
    def test_dashboard_version_comes_from_version_env(self) -> None:
        self.assertEqual(homepage_release.dashboard_version(), "0.1.0")

    def test_compose_command_uses_stable_project_name(self) -> None:
        command = homepage_release.compose_command(Path("/release"), "config", "--quiet")
        self.assertEqual(command[0:4], ["docker", "compose", "--project-name", "homepage"])
        compose_file = Path(command[command.index("--file") + 1])
        self.assertEqual(compose_file.name, "compose.yaml")

    @patch("scripts.homepage_release.time.sleep")
    @patch("scripts.homepage_release.urllib.request.urlopen")
    @patch("scripts.homepage_release.run")
    def test_verify_requires_both_services_and_http_success(
        self,
        mock_run: MagicMock,
        mock_urlopen: MagicMock,
        _mock_sleep: MagicMock,
    ) -> None:
        mock_run.return_value = json.dumps(
            [
                {"Service": "homepage", "State": "running", "Health": ""},
                {"Service": "glances", "State": "running", "Health": "healthy"},
            ]
        )
        response = MagicMock()
        response.status = 200
        mock_urlopen.return_value.__enter__.return_value = response

        homepage_release.verify(Path("/release"), "http://127.0.0.1:3000", 1, 0)

    @patch("scripts.homepage_release.run")
    def test_verify_rejects_a_missing_service(self, mock_run: MagicMock) -> None:
        mock_run.return_value = json.dumps(
            [{"Service": "homepage", "State": "running", "Health": ""}]
        )
        with self.assertRaisesRegex(homepage_release.ReleaseError, "glances"):
            homepage_release.verify(Path("/release"), "http://127.0.0.1:3000", 1, 0)

    def test_deployment_lock_creates_lock_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with homepage_release.deployment_lock(root):
                self.assertTrue((root / "deployment.lock").exists())
            self.assertIn("pid=", (root / "deployment.lock").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
