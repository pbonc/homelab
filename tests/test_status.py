from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from labctl.commands import status


class StatusTests(unittest.TestCase):
    def test_schema_declares_the_runtime_contract_version(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "status-v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], status.SCHEMA_VERSION)
        self.assertEqual(set(schema["$defs"]["status"]["enum"]), status.VALID_STATUSES)

    def test_deployed_release_reads_required_metadata(self) -> None:
        payload = {
            "version": "0.1.0",
            "git_commit": "a" * 40,
            "deployer": "tester",
            "deployed_at": "2026-07-15T16:41:23+00:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deployed.json").write_text(json.dumps(payload), encoding="utf-8")
            release = status._deployed_release(root)

        self.assertEqual(release["status"], "deployed")
        self.assertEqual(release["version"], "0.1.0")

    def test_deployed_release_rejects_incomplete_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deployed.json").write_text('{"version":"0.1.0"}', encoding="utf-8")
            self.assertEqual(status._deployed_release(root), {"status": "invalid"})

    @patch("labctl.commands.status.shutil.which", return_value="docker")
    @patch("labctl.commands.status.subprocess.run")
    def test_container_status_recognizes_healthy_glances(
        self,
        mock_run: MagicMock,
        _mock_which: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="running healthy\n")
        service = status._container_status("glances")
        self.assertEqual(service["status"], "healthy")
        self.assertIn("glances", mock_run.call_args.args[0])

    def test_overall_status_uses_criticality_and_explicit_unavailable(self) -> None:
        unavailable = status._check(
            "docker.service", "runtime", "critical", "unavailable", "unsupported", "now"
        )
        self.assertEqual(status._overall_status([unavailable]), "unavailable")

        healthy = status._check(
            "homepage.container", "runtime", "critical", "healthy", "ok", "now"
        )
        warning = status._check(
            "glances.container", "runtime", "informational", "degraded", "partial", "now"
        )
        self.assertEqual(status._overall_status([healthy, warning]), "degraded")

        stale = status._check(
            "telemetry.collector", "application", "important", "stale", "old data", "now"
        )
        self.assertEqual(status._overall_status([healthy, stale]), "degraded")

        failed = status._check(
            "docker.service", "runtime", "critical", "failed", "inactive", "now"
        )
        self.assertEqual(status._overall_status([failed, healthy]), "failed")

    @patch("labctl.commands.status._deployed_release")
    @patch("labctl.commands.status._container_status")
    @patch("labctl.commands.status._docker_service_status")
    @patch("labctl.commands.status._git_branch", return_value="main")
    def test_status_payload_is_versioned_and_uses_utc_timestamps(
        self,
        _mock_branch: MagicMock,
        mock_docker: MagicMock,
        mock_container: MagicMock,
        mock_release: MagicMock,
    ) -> None:
        mock_docker.return_value = {
            "level": "pass",
            "state": "active",
            "status": "healthy",
        }
        mock_container.return_value = {
            "level": "pass",
            "state": "running",
            "health": "healthy",
            "status": "healthy",
        }
        mock_release.return_value = {
            "status": "deployed",
            "version": "0.1.0",
            "git_commit": "a" * 40,
            "deployer": "tester",
            "deployed_at": "2026-07-17T12:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            payload = status._status_payload(
                Path(directory),
                observed_at=datetime(2026, 7, 17, 12, 30, tzinfo=UTC),
            )

        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["generated_at"], "2026-07-17T12:30:00+00:00")
        self.assertEqual(payload["overall_status"], "healthy")
        self.assertEqual(len(payload["checks"]), 4)
        self.assertTrue(all(check["observed_at"] == payload["generated_at"] for check in payload["checks"]))

    def test_exit_codes_only_fail_on_confirmed_actionable_states(self) -> None:
        self.assertEqual(status.EXIT_CODES["healthy"], 0)
        self.assertEqual(status.EXIT_CODES["unavailable"], 0)
        self.assertEqual(status.EXIT_CODES["degraded"], 1)
        self.assertEqual(status.EXIT_CODES["failed"], 2)


if __name__ == "__main__":
    unittest.main()
