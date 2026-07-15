from __future__ import annotations

import json
import os
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


def _docker_service_status() -> dict[str, str]:
    if shutil.which("systemctl") is None:
        return {"level": "info", "state": "unavailable", "status": "unavailable"}

    result = subprocess.run(
        ["systemctl", "is-active", "docker"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip() == "active":
        return {"level": "pass", "state": "active", "status": "healthy"}
    return {"level": "fail", "state": "inactive", "status": "unhealthy"}


def _container_status(container: str) -> dict[str, str]:
    if shutil.which("docker") is None:
        return {
            "level": "info",
            "state": "unavailable",
            "health": "unavailable",
            "status": "unavailable",
        }

    result = subprocess.run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return {
            "level": "fail",
            "state": "not-found",
            "health": "unknown",
            "status": "unhealthy",
        }

    status_output = result.stdout.strip()
    if not status_output:
        return {
            "level": "fail",
            "state": "unknown",
            "health": "unknown",
            "status": "unhealthy",
        }

    status, _, health = status_output.partition(" ")
    if status == "running" and health == "healthy":
        return {
            "level": "pass",
            "state": "running",
            "health": "healthy",
            "status": "healthy",
        }
    if status == "running" and health == "no-healthcheck":
        return {
            "level": "warn",
            "state": "running",
            "health": "no-healthcheck",
            "status": "warning",
        }
    if status == "running" and health == "unhealthy":
        return {
            "level": "fail",
            "state": "running",
            "health": "unhealthy",
            "status": "unhealthy",
        }
    return {
        "level": "fail",
        "state": status or "unknown",
        "health": health or "unknown",
        "status": "unhealthy",
    }


def _deployed_release(deploy_root: Path) -> dict[str, str]:
    metadata_path = deploy_root / "deployed.json"
    if not metadata_path.exists():
        return {"status": "unavailable"}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"status": "invalid"}

    required = ("version", "git_commit", "deployer", "deployed_at")
    if not all(isinstance(payload.get(field), str) and payload[field] for field in required):
        return {"status": "invalid"}
    return {"status": "deployed", **{field: payload[field] for field in required}}


def _print_docker_service_status(service: dict[str, str]) -> None:
    level = service["level"]
    if level == "info":
        print("[INFO] Docker service check unavailable on this platform.")
    elif level == "pass":
        print("[PASS] Docker: active")
    else:
        print("[FAIL] Docker: inactive")


def _print_container_status(name: str, service: dict[str, str]) -> None:
    level = service["level"]
    state = service["state"]
    health = service.get("health", "unknown")

    if level == "info":
        print(f"[INFO] {name}: Docker CLI unavailable")
    elif level == "pass":
        print(f"[PASS] {name}: running / healthy")
    elif level == "warn" and state == "running" and health == "no-healthcheck":
        print(f"[WARN] {name}: running / no healthcheck")
    elif state == "running" and health == "unhealthy":
        print(f"[FAIL] {name}: running / unhealthy")
    elif state == "not-found":
        print(f"[FAIL] {name}: not found")
    elif state == "unknown":
        print(f"[FAIL] {name}: unknown")
    else:
        print(f"[FAIL] {name}: {state}")


def _print_release(release: dict[str, str]) -> None:
    if release["status"] == "deployed":
        commit = release["git_commit"][:12]
        print(
            f"[PASS] Release: v{release['version']} / {commit} / "
            f"{release['deployer']} / {release['deployed_at']}"
        )
    elif release["status"] == "invalid":
        print("[FAIL] Release: deployed.json is invalid")
    else:
        print("[INFO] Release: no managed deployment metadata found")


def run_status(json_output: bool = False) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    branch = _git_branch(repo_root)

    expected_paths = [
        repo_root / "ansible",
        repo_root / "docker",
        repo_root / "kubernetes",
        repo_root / "terraform",
        repo_root / "docker" / "homepage" / "compose.yaml",
    ]
    path_statuses: dict[str, str] = {}
    for path in expected_paths:
        rel = path.relative_to(repo_root)
        if path.exists():
            path_statuses[str(rel)] = "present"
        else:
            path_statuses[str(rel)] = "missing"

    docker_status = _docker_service_status()
    homepage_status = _container_status("homepage")
    glances_status = _container_status("glances")
    deploy_root = Path(os.environ.get("HOMEPAGE_DEPLOY_ROOT", "/srv/homelab/homepage"))
    release = _deployed_release(deploy_root)

    if json_output:
        payload = {
            "repository": {
                "root": str(repo_root),
                "branch": branch,
            },
            "paths": path_statuses,
            "services": {
                "docker": {
                    "state": docker_status["state"],
                    "status": docker_status["status"],
                },
                "homepage": {
                    "state": homepage_status["state"],
                    "health": homepage_status["health"],
                    "status": homepage_status["status"],
                },
                "glances": {
                    "state": glances_status["state"],
                    "health": glances_status["health"],
                    "status": glances_status["status"],
                },
            },
            "deployment": release,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("== Homelab Status ==")
    print()

    print("-- Repository --")
    _ok("Root", str(repo_root))
    _ok("Branch", branch)

    print()
    print("-- Expected Paths --")
    for rel, state in path_statuses.items():
        if state == "present":
            _ok(rel, state)
        else:
            _warn(rel, state)

    print()
    print("-- Services --")
    _print_docker_service_status(docker_status)
    _print_container_status("Homepage", homepage_status)
    _print_container_status("Glances", glances_status)
    _print_release(release)

    print()
    print("Status checks complete.")
    return 0
