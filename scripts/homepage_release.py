#!/usr/bin/env python3
"""Validate, deploy, verify, and roll back Homepage releases on brain."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "docker" / "homepage"
DEFAULT_DEPLOY_ROOT = Path("/srv/homelab/homepage")
DEFAULT_URL = "http://127.0.0.1:3000"
PROJECT_NAME = "homepage"


class ReleaseError(RuntimeError):
    """A deployment-contract operation failed."""


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if capture else ""
        raise ReleaseError(f"command failed ({result.returncode}): {' '.join(command)}{': ' + detail if detail else ''}")
    return result.stdout.strip() if capture else ""


def git_value(*args: str) -> str:
    return run(["git", "-C", str(REPO_ROOT), *args], capture=True)


def dashboard_version() -> str:
    for line in (SOURCE_DIR / "version.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("HOMEPAGE_VAR_DASHBOARD_VERSION="):
            return line.partition("=")[2].strip()
    raise ReleaseError("docker/homepage/version.env does not define HOMEPAGE_VAR_DASHBOARD_VERSION")


def compose_command(release: Path, *args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        PROJECT_NAME,
        "--file",
        str(release / "compose.yaml"),
        *args,
    ]


def validate() -> None:
    run([sys.executable, str(REPO_ROOT / "scripts" / "validate_homepage.py")])
    run(compose_command(SOURCE_DIR, "config", "--quiet"))
    print("[PASS] Homepage source and Compose configuration are valid")


@contextmanager
def deployment_lock(deploy_root: Path):
    deploy_root.mkdir(parents=True, exist_ok=True)
    lock_path = deploy_root / "deployment.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            if os.name == "nt":
                lock_file.seek(0)
                if lock_file.read(1) == "":
                    lock_file.write("\n")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise ReleaseError(f"another Homepage deployment holds {lock_path}") from exc
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"pid={os.getpid()}\n")
        lock_file.flush()
        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def link_target(link: Path) -> Path | None:
    if not link.is_symlink():
        return None
    target = Path(os.readlink(link))
    return target if target.is_absolute() else (link.parent / target).resolve()


def atomic_link(link: Path, target: Path) -> None:
    temporary = link.with_name(f".{link.name}.{os.getpid()}.tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target, target_is_directory=True)
    os.replace(temporary, link)


def release_metadata() -> dict[str, str]:
    commit = git_value("rev-parse", "HEAD")
    dirty = git_value("status", "--porcelain")
    if dirty:
        raise ReleaseError("refusing to deploy a dirty working tree")
    return {
        "version": dashboard_version(),
        "git_commit": commit,
        "deployer": os.environ.get("GITHUB_ACTOR") or os.environ.get("USER") or "unknown",
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }


def write_metadata(path: Path, metadata: dict[str, str]) -> None:
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify(release: Path, url: str, attempts: int, interval: float) -> None:
    ps = run(compose_command(release, "ps", "--format", "json"), capture=True)
    if not ps:
        raise ReleaseError("Compose reports no Homepage services")

    try:
        parsed = json.loads(ps)
        services = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        try:
            services = [json.loads(line) for line in ps.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"Compose returned invalid service JSON: {exc}") from exc
    service_names = {service.get("Service") for service in services}
    missing = {"homepage", "glances"} - service_names
    if missing:
        raise ReleaseError("Compose services are missing: " + ", ".join(sorted(missing)))
    failures = []
    for service in services:
        state = service.get("State")
        health = service.get("Health", "")
        if state != "running" or health == "unhealthy":
            failures.append(f"{service.get('Service', 'unknown')}={state}/{health or 'no-healthcheck'}")
    if failures:
        raise ReleaseError("unhealthy Compose services: " + ", ".join(failures))

    last_error = "no response"
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 400:
                    print(f"[PASS] Homepage verified at {url} (HTTP {response.status})")
                    return
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(interval)
    raise ReleaseError(f"Homepage verification failed at {url}: {last_error}")


def activate(release: Path, deploy_root: Path) -> None:
    atomic_link(deploy_root / "current", release)
    run(compose_command(release, "up", "--detach", "--remove-orphans"))


def deploy(deploy_root: Path, url: str, attempts: int, interval: float) -> None:
    validate()
    metadata = release_metadata()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    release_id = f"{metadata['version']}-{metadata['git_commit'][:12]}-{timestamp}"
    releases = deploy_root / "releases"
    release = releases / release_id

    with deployment_lock(deploy_root):
        releases.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="homepage-stage-", dir=releases) as stage_name:
            stage = Path(stage_name)
            shutil.copytree(
                SOURCE_DIR,
                stage,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("logs", "kubernetes.yaml", "status.json"),
            )
            write_metadata(stage / "release.json", metadata)
            stage.rename(release)

        current_link = deploy_root / "current"
        previous = link_target(current_link)
        if previous and previous != release:
            atomic_link(deploy_root / "previous", previous)

        try:
            activate(release, deploy_root)
            verify(release, url, attempts, interval)
        except Exception:
            if previous and previous.exists():
                print(f"[WARN] Verification failed; restoring {previous.name}", file=sys.stderr)
                activate(previous, deploy_root)
            else:
                print(
                    "[WARN] Verification failed with no managed release to restore; "
                    "leaving the candidate running for inspection",
                    file=sys.stderr,
                )
            raise

        write_metadata(deploy_root / "deployed.json", metadata)
        print(f"[PASS] Deployed Homepage {release_id}")


def rollback(deploy_root: Path, url: str, attempts: int, interval: float) -> None:
    with deployment_lock(deploy_root):
        current = link_target(deploy_root / "current")
        previous = link_target(deploy_root / "previous")
        if not previous or not previous.exists():
            raise ReleaseError("no last-known-good Homepage release is available")

        activate(previous, deploy_root)
        verify(previous, url, attempts, interval)
        if current and current.exists():
            atomic_link(deploy_root / "previous", current)
        metadata_path = previous / "release.json"
        if metadata_path.exists():
            shutil.copy2(metadata_path, deploy_root / "deployed.json")
        print(f"[PASS] Rolled back Homepage to {previous.name}")


def current_release(deploy_root: Path) -> Path:
    current = link_target(deploy_root / "current")
    if not current or not current.exists():
        raise ReleaseError(f"no deployed Homepage release under {deploy_root}")
    return current


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate", "deploy", "verify", "rollback"),
    )
    parser.add_argument(
        "--deploy-root",
        type=Path,
        default=Path(os.environ.get("HOMEPAGE_DEPLOY_ROOT", DEFAULT_DEPLOY_ROOT)),
    )
    parser.add_argument("--url", default=os.environ.get("HOMEPAGE_VERIFY_URL", DEFAULT_URL))
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--interval", type=float, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "validate":
            validate()
        elif args.command == "deploy":
            deploy(args.deploy_root, args.url, args.attempts, args.interval)
        elif args.command == "verify":
            verify(current_release(args.deploy_root), args.url, args.attempts, args.interval)
        else:
            rollback(args.deploy_root, args.url, args.attempts, args.interval)
    except (OSError, ReleaseError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
