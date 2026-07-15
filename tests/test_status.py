from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from labctl.commands import status


class StatusTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
