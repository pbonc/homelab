from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _ok(label: str, value: str) -> None:
    print(f"[OK]   {label}: {value}")


def _warn(label: str, value: str) -> None:
    print(f"[WARN] {label}: {value}")


def _git_branch(repo_root: Path) -> str:
    if shutil.which("git") is None:
        return "git not installed"

    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def run_status() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    print("== Homelab Status ==")
    print()

    print("-- Repository --")
    _ok("Root", str(repo_root))
    _ok("Branch", _git_branch(repo_root))

    print()
    print("-- Expected Paths --")
    expected_paths = [
        repo_root / "ansible",
        repo_root / "docker",
        repo_root / "kubernetes",
        repo_root / "terraform",
        repo_root / "docker" / "homepage" / "compose.yaml",
    ]
    for path in expected_paths:
        rel = path.relative_to(repo_root)
        if path.exists():
            _ok(str(rel), "present")
        else:
            _warn(str(rel), "missing")

    print()
    print("Status checks complete.")
    return 0
