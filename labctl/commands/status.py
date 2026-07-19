from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA_VERSION = "1.0.0"
VALID_STATUSES = {"healthy", "degraded", "stale", "unavailable", "failed"}
EXIT_CODES = {"healthy": 0, "unavailable": 0, "degraded": 1, "stale": 1, "failed": 2}
HTTP_WARNING_MS = 500.0
HTTP_TIMEOUT_SECONDS = 3.0
TELEMETRY_STALE_SECONDS = 180.0

CONTAINERS = (
    ("homepage.container", "homepage", "critical"),
    ("homepage.proxy", "homepage-docker-proxy", "important"),
    ("glances.container", "glances", "informational"),
    ("telemetry.collector.container", "telemetry-collector", "important"),
    ("telemetry.influxdb.container", "influxdb", "important"),
    ("telemetry.grafana.container", "grafana", "important"),
    ("security.aikido.container", "security-status", "important"),
    ("study.deck.container", "study-deck", "informational"),
    ("observability.loki.container", "loki", "important"),
    ("observability.alloy.container", "alloy", "important"),
    ("observability.proxy.container", "observability-docker-proxy", "informational"),
)

ENDPOINTS = (
    ("homepage.http", "http://127.0.0.1:3000/api/healthcheck", "critical", "homepage"),
    ("telemetry.collector.http", "http://127.0.0.1:8000/api/health", "important", "telemetry"),
    ("telemetry.influxdb.http", "http://127.0.0.1:8086/health", "important", "influxdb"),
    ("telemetry.grafana.http", "http://127.0.0.1:3001/api/health", "important", "grafana"),
    ("security.aikido.http", "http://127.0.0.1:8010/api/status", "important", "aikido"),
    ("study.deck.http", "http://192.168.1.23:8020/api/health", "informational", "study"),
    ("observability.loki.http", "http://192.168.1.23:3100/ready", "important", "loki"),
)


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
    return {"level": "fail", "state": "inactive", "status": "failed"}


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
            "status": "failed",
        }

    status_output = result.stdout.strip()
    if not status_output:
        return {
            "level": "fail",
            "state": "unknown",
            "health": "unknown",
            "status": "failed",
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
            "status": "degraded",
        }
    if status == "running" and health == "unhealthy":
        return {
            "level": "fail",
            "state": "running",
            "health": "unhealthy",
            "status": "failed",
        }
    return {
        "level": "fail",
        "state": status or "unknown",
        "health": health or "unknown",
        "status": "failed",
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


def _runner_status() -> dict[str, str]:
    if shutil.which("systemctl") is None:
        return {"state": "unavailable", "status": "unavailable", "unit": ""}
    result = subprocess.run(
        [
            "systemctl",
            "list-units",
            "--type=service",
            "--all",
            "--no-legend",
            "actions.runner.*",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return {"state": "not-found", "status": "failed", "unit": ""}
    fields = lines[0].split()
    unit = fields[0]
    active = len(fields) > 2 and fields[2] == "active"
    running = len(fields) > 3 and fields[3] == "running"
    return {
        "state": "running" if active and running else "inactive",
        "status": "healthy" if active and running else "failed",
        "unit": unit,
    }


def _http_probe(url: str, kind: str, now: datetime | None = None) -> dict[str, object]:
    started = time.perf_counter()
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "labctl/1"})
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(65536).decode("utf-8", "replace")
            code = response.status
    except HTTPError as exc:
        return {"status": "failed", "summary": f"HTTP {exc.code}", "http_status": exc.code}
    except (URLError, TimeoutError, OSError) as exc:
        return {"status": "failed", "summary": type(exc).__name__, "http_status": None}

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    status = "degraded" if latency_ms > HTTP_WARNING_MS else "healthy"
    summary = f"HTTP {code} in {latency_ms:.1f} ms"
    payload: object = None
    if body.lstrip().startswith(("{", "[")):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {
                "status": "failed",
                "summary": "invalid JSON response",
                "http_status": code,
                "latency_ms": latency_ms,
            }

    if kind == "telemetry" and isinstance(payload, dict):
        if payload.get("status") != "healthy":
            status = "failed"
        received = payload.get("last_received_at")
        if isinstance(received, str):
            try:
                observed = datetime.fromisoformat(received.replace("Z", "+00:00"))
                age = ((now or datetime.now(UTC)) - observed).total_seconds()
                if age > TELEMETRY_STALE_SECONDS and status != "failed":
                    status = "stale"
                summary += f"; data age {max(0, round(age))} s"
            except ValueError:
                status = "failed"
                summary += "; invalid freshness timestamp"
    elif kind == "influxdb" and isinstance(payload, dict) and payload.get("status") != "pass":
        status = "failed"
    elif kind == "grafana" and isinstance(payload, dict) and payload.get("database") != "ok":
        status = "failed"
    elif kind == "aikido" and isinstance(payload, dict):
        if payload.get("stale") is True:
            status = "stale"
        elif payload.get("status") == "unavailable":
            status = "degraded"

    return {
        "status": status,
        "summary": summary,
        "http_status": code,
        "latency_ms": latency_ms,
    }


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


def _check(
    check_id: str,
    category: str,
    criticality: str,
    status: str,
    summary: str,
    observed_at: str,
    **details: object,
) -> dict[str, object]:
    if status not in VALID_STATUSES:
        raise ValueError(f"unsupported status: {status}")
    return {
        "id": check_id,
        "category": category,
        "criticality": criticality,
        "status": status,
        "summary": summary,
        "observed_at": observed_at,
        "details": details,
    }


def _overall_status(checks: list[dict[str, object]]) -> str:
    statuses = [str(check["status"]) for check in checks]
    if any(
        check["criticality"] == "critical" and check["status"] == "failed"
        for check in checks
    ):
        return "failed"
    if statuses and all(status == "unavailable" for status in statuses):
        return "unavailable"
    if any(status in {"failed", "degraded", "stale"} for status in statuses):
        return "degraded"
    if any(
        check["criticality"] == "critical" and check["status"] == "unavailable"
        for check in checks
    ):
        return "degraded"
    return "healthy"


def _status_payload(repo_root: Path, observed_at: datetime | None = None) -> dict[str, object]:
    now = observed_at or datetime.now(UTC)
    timestamp = now.astimezone(UTC).isoformat()
    branch = _git_branch(repo_root)
    expected_paths = [
        repo_root / "ansible",
        repo_root / "docker",
        repo_root / "kubernetes",
        repo_root / "terraform",
        repo_root / "docker" / "homepage" / "compose.yaml",
    ]
    paths = {
        str(path.relative_to(repo_root)): "present" if path.exists() else "missing"
        for path in expected_paths
    }

    docker = _docker_service_status()
    unavailable_container = {
        "level": "info",
        "state": "unavailable",
        "health": "unavailable",
        "status": "unavailable",
    }
    containers = {
        name: (
            dict(unavailable_container)
            if docker["status"] == "unavailable"
            else _container_status(name)
        )
        for _check_id, name, _criticality in CONTAINERS
    }
    runner = _runner_status()
    deploy_root = Path(os.environ.get("HOMEPAGE_DEPLOY_ROOT", "/srv/homelab/homepage"))
    release = _deployed_release(deploy_root)

    release_status = {
        "deployed": "healthy",
        "invalid": "failed",
        "unavailable": "unavailable",
    }[release["status"]]
    checks = [
        _check(
            "docker.service",
            "runtime",
            "critical",
            docker["status"],
            f"Docker service is {docker['state']}",
            timestamp,
            state=docker["state"],
        ),
        *[
            _check(
                check_id,
                "runtime",
                criticality,
                containers[name]["status"],
                f"{name} container is {containers[name]['state']} / {containers[name]['health']}",
                timestamp,
                state=containers[name]["state"],
                health=containers[name]["health"],
                container=name,
            )
            for check_id, name, criticality in CONTAINERS
        ],
        _check(
            "github.runner",
            "runtime",
            "important",
            runner["status"],
            f"GitHub Actions runner is {runner['state']}",
            timestamp,
            state=runner["state"],
            unit=runner["unit"],
        ),
        _check(
            "homepage.release",
            "deployment",
            "important",
            release_status,
            f"Homepage release metadata is {release['status']}",
            timestamp,
            **{key: value for key, value in release.items() if key != "status"},
        ),
    ]
    if docker["status"] == "unavailable":
        for check_id, url, criticality, _kind in ENDPOINTS:
            checks.append(
                _check(
                    check_id,
                    "http",
                    criticality,
                    "unavailable",
                    "HTTP probe is unavailable on this platform",
                    timestamp,
                    url=url,
                )
            )
    else:
        for check_id, url, criticality, kind in ENDPOINTS:
            probe = dict(_http_probe(url, kind, now=now))
            checks.append(
                _check(
                    check_id,
                    "http",
                    criticality,
                    str(probe.pop("status")),
                    str(probe.pop("summary")),
                    timestamp,
                    url=url,
                    **probe,
                )
            )
    overall = _overall_status(checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "overall_status": overall,
        "context": {
            "repository_root": str(repo_root),
            "branch": branch,
            "paths": paths,
        },
        "checks": checks,
    }


def run_status(json_output: bool = False) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    payload = _status_payload(repo_root)
    exit_code = EXIT_CODES[str(payload["overall_status"])]

    if json_output:
        print(json.dumps(payload, indent=2))
        return exit_code

    print("== Homelab Status ==")
    print()
    print(f"Overall: {str(payload['overall_status']).upper()}")
    print(f"Schema: {payload['schema_version']}")
    print()
    for check in payload["checks"]:
        label = str(check["id"])
        status = str(check["status"]).upper()
        print(f"[{status}] {label}: {check['summary']}")

    print()
    print("Status checks complete.")
    return exit_code
