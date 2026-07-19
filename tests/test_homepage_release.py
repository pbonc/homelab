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
                {"Service": "docker-proxy", "State": "running", "Health": "healthy"},
            ]
        )
        response = MagicMock()
        response.status = 200
        mock_urlopen.return_value.__enter__.return_value = response

        homepage_release.verify(Path("/release"), "http://127.0.0.1:3000", 1, 0)

    @patch("scripts.homepage_release.time.sleep")
    @patch("scripts.homepage_release.urllib.request.urlopen")
    @patch("scripts.homepage_release.run")
    def test_verify_accepts_compose_v5_json_lines(
        self,
        mock_run: MagicMock,
        mock_urlopen: MagicMock,
        _mock_sleep: MagicMock,
    ) -> None:
        mock_run.return_value = "\n".join(
            [
                json.dumps({"Service": "homepage", "State": "running", "Health": "healthy"}),
                json.dumps({"Service": "glances", "State": "running", "Health": "healthy"}),
                json.dumps({"Service": "docker-proxy", "State": "running", "Health": "healthy"}),
            ]
        )
        response = MagicMock()
        response.status = 200
        mock_urlopen.return_value.__enter__.return_value = response

        homepage_release.verify(Path("/release"), "http://127.0.0.1:3000", 1, 0)

    @patch("scripts.homepage_release.time.sleep")
    @patch("scripts.homepage_release.urllib.request.urlopen")
    @patch("scripts.homepage_release.run")
    def test_verify_retries_a_connection_reset_during_startup(
        self,
        mock_run: MagicMock,
        mock_urlopen: MagicMock,
        _mock_sleep: MagicMock,
    ) -> None:
        mock_run.return_value = "\n".join(
            [
                json.dumps({"Service": "homepage", "State": "running", "Health": "healthy"}),
                json.dumps({"Service": "glances", "State": "running", "Health": "healthy"}),
                json.dumps({"Service": "docker-proxy", "State": "running", "Health": "healthy"}),
            ]
        )
        response = MagicMock()
        response.status = 200
        successful_request = MagicMock()
        successful_request.__enter__.return_value = response
        mock_urlopen.side_effect = [ConnectionResetError(104, "Connection reset by peer"), successful_request]

        homepage_release.verify(Path("/release"), "http://127.0.0.1:3000", 2, 0)

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

    def test_deployment_event_is_versioned_and_append_only(self) -> None:
        metadata = {
            "version": "0.1.0",
            "git_commit": "a" * 40,
            "deployer": "tester",
            "deployed_at": "2026-07-19T00:00:00+00:00",
        }
        event = homepage_release.deployment_event(
            metadata,
            operation="deploy",
            result="successful",
            release_id="release-one",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            homepage_release.append_deployment_event(root, event)
            homepage_release.append_deployment_event(root, event)
            records = [
                json.loads(line)
                for line in (root / homepage_release.EVENT_JOURNAL)
                .read_text(encoding="utf-8")
                .splitlines()
            ]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["schema_version"], "1.0.0")
        self.assertEqual(records[0]["result"], "successful")
        self.assertFalse(records[0]["rollback_performed"])

    @patch("scripts.homepage_release.urllib.request.urlopen", side_effect=OSError("offline"))
    @patch("scripts.homepage_release.append_deployment_event", side_effect=OSError("offline"))
    def test_event_journal_failure_does_not_escape(
        self, _mock_append: MagicMock, _mock_urlopen: MagicMock
    ) -> None:
        homepage_release.record_deployment_event(Path("/unused"), {"event": "test"})

    @patch("scripts.homepage_release.urllib.request.urlopen")
    def test_event_publication_posts_json(self, mock_urlopen: MagicMock) -> None:
        response = MagicMock()
        response.status = 202
        mock_urlopen.return_value.__enter__.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            homepage_release.record_deployment_event(Path(directory), {"event": "test"})
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(json.loads(request.data), {"event": "test"})


if __name__ == "__main__":
    unittest.main()
