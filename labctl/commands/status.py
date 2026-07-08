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


def _docker_service_status() -> None:
    if shutil.which("systemctl") is None:
        print("[INFO] Docker service check unavailable on this platform.")
        return

    result = subprocess.run(
        ["systemctl", "is-active", "docker"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip() == "active":
        print("[PASS] Docker: active")
    else:
        print("[FAIL] Docker: inactive")


def _homepage_container_status() -> None:
    if shutil.which("docker") is None:
        print("[INFO] Homepage: Docker CLI unavailable")
        return

    result = subprocess.run(
        [
            "docker",
            "inspect",
            "homepage",
            "--format",
            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "no such object" in stderr or "not found" in stderr:
            print("[FAIL] Homepage: not found")
        else:
            print("[FAIL] Homepage: not found")
        return

    status_output = result.stdout.strip()
    if not status_output:
        print("[FAIL] Homepage: unknown")
        return

    status, _, health = status_output.partition(" ")
    if status == "running" and health == "healthy":
        print("[PASS] Homepage: running / healthy")
    elif status == "running" and health == "no-healthcheck":
        print("[WARN] Homepage: running / no healthcheck")
    elif status == "running" and health == "unhealthy":
        print("[FAIL] Homepage: running / unhealthy")
    else:
        print(f"[FAIL] Homepage: {status}")


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
    print("-- Services --")
    _docker_service_status()
    _homepage_container_status()

    print()
    print("Status checks complete.")
    return 0
