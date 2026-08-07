from __future__ import annotations

import argparse
import ipaddress
import json
import secrets
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import quiz_range_compose  # noqa: E402
import quiz_scenario  # noqa: E402


RUNTIME_DIR = Path(".runtime/quiz-range")
SCENARIO_FILE = "scenario.json"
COMPOSE_FILE = "compose.json"
IMAGE_BUILDS = (
    (quiz_range_compose.TRAILHEAD_IMAGE, Path("docker/trailhead-rentals")),
    (quiz_range_compose.DECOY_IMAGE, Path("docker/quiz-decoy")),
    (quiz_range_compose.ATTACKER_IMAGE, Path("docker/quiz-attacker")),
)
Run = Callable[..., subprocess.CompletedProcess[str]]


def runtime_paths(runtime_dir: Path) -> tuple[Path, Path]:
    return runtime_dir / SCENARIO_FILE, runtime_dir / COMPOSE_FILE


def load_private(runtime_dir: Path) -> tuple[dict[str, Any], Path]:
    scenario_path, compose_path = runtime_paths(runtime_dir)
    if not scenario_path.is_file() or not compose_path.is_file():
        raise RuntimeError("quiz range is not prepared; run quiz-range-prepare first")
    return json.loads(scenario_path.read_text(encoding="utf-8")), compose_path


def prepare(
    seed: int,
    decoys: int,
    excluded: list[ipaddress.IPv4Network],
    runtime_dir: Path = RUNTIME_DIR,
) -> dict[str, Any]:
    live_networks = quiz_scenario.discover_docker_networks()
    scenario = quiz_scenario.generate_scenario(
        seed=seed,
        excluded=[*excluded, *live_networks],
        decoy_count=decoys,
    )
    compose = quiz_range_compose.render_compose(scenario)
    scenario_path, compose_path = runtime_paths(runtime_dir)
    quiz_range_compose.write_private_json(scenario_path, scenario)
    quiz_range_compose.write_private_json(compose_path, compose)
    return scenario


def checked_run(run: Run, command: list[str]) -> subprocess.CompletedProcess[str]:
    result = run(command, capture_output=True, check=False, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(detail)
    return result


def compose_command(compose_path: Path, *arguments: str) -> list[str]:
    return ["docker", "compose", "--file", str(compose_path), *arguments]


def deploy(runtime_dir: Path = RUNTIME_DIR, run: Run = subprocess.run) -> dict[str, Any]:
    scenario, compose_path = load_private(runtime_dir)
    for image, context in IMAGE_BUILDS:
        checked_run(run, ["docker", "build", "--tag", image, str(context)])
    checked_run(
        run,
        compose_command(compose_path, "up", "--detach", "--wait"),
    )
    return scenario


def expected_surface(scenario: dict[str, Any]) -> set[tuple[str, int]]:
    surface = {(scenario["target"]["address"], 8080)}
    surface.update((item["address"], int(item["port"])) for item in scenario["decoys"])
    return surface


def parse_nmap_xml(payload: str) -> set[tuple[str, int]]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise RuntimeError("attacker returned invalid nmap XML") from exc
    observed: set[tuple[str, int]] = set()
    for host in root.findall("host"):
        address = host.find("address")
        if address is None or not address.get("addr"):
            continue
        for port in host.findall("./ports/port"):
            state = port.find("state")
            if state is not None and state.get("state") == "open":
                observed.add((address.get("addr", ""), int(port.get("portid", "0"))))
    return observed


def attacker_run(
    compose_path: Path,
    shell_command: str,
    run: Run,
) -> subprocess.CompletedProcess[str]:
    return run(
        compose_command(
            compose_path,
            "--profile",
            "attacker",
            "run",
            "--rm",
            "--no-deps",
            "attacker",
            "-c",
            shell_command,
        ),
        capture_output=True,
        check=False,
        text=True,
    )


def verify(runtime_dir: Path = RUNTIME_DIR, run: Run = subprocess.run) -> dict[str, int]:
    scenario, compose_path = load_private(runtime_dir)
    surface = expected_surface(scenario)
    ports = ",".join(str(port) for port in sorted({item[1] for item in surface}))
    scan = attacker_run(
        compose_path,
        f"nmap -sT -Pn -n -p {ports} -oX - {scenario['authorized_cidr']}",
        run,
    )
    if scan.returncode != 0:
        raise RuntimeError(scan.stderr.strip() or "attacker scan failed")
    observed = parse_nmap_xml(scan.stdout)
    if observed != surface:
        missing = sorted(surface - observed)
        unexpected = sorted(observed - surface)
        raise RuntimeError(
            f"scan surface mismatch: missing={len(missing)} unexpected={len(unexpected)}"
        )

    checks = [(scenario["target"]["address"], 8080, "/api/health", 200)]
    checks.extend(
        (
            item["address"],
            int(item["port"]),
            route,
            401 if item["profile_id"] == "maintenance" and route == "/work-orders" else 200,
        )
        for item in scenario["decoys"]
        for route in item["expected_routes"]
    )
    for address, port, route, expected_status in checks:
        result = attacker_run(
            compose_path,
            "curl --silent --show-error --output /dev/null --write-out '%{http_code}' "
            f"--connect-timeout 2 --max-time 5 http://{address}:{port}{route}",
            run,
        )
        if result.returncode != 0 or result.stdout.strip() != str(expected_status):
            raise RuntimeError(
                f"expected HTTP {expected_status} failed at {address}:{port}{route}"
            )

    for prohibited in ("http://192.168.1.23:3000", "http://1.1.1.1"):
        result = attacker_run(
            compose_path,
            "curl --silent --connect-timeout 2 --max-time 3 "
            f"{prohibited} >/dev/null",
            run,
        )
        if result.returncode == 0:
            raise RuntimeError(f"isolation failure: attacker reached {prohibited}")

    return {"services": len(surface), "routes": len(checks)}


def destroy(runtime_dir: Path = RUNTIME_DIR, run: Run = subprocess.run) -> None:
    _, compose_path = load_private(runtime_dir)
    checked_run(
        run,
        compose_command(
            compose_path,
            "--profile",
            "attacker",
            "down",
            "--remove-orphans",
        ),
    )
    shutil.rmtree(runtime_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage a private disposable quiz range")
    parser.add_argument(
        "action", choices=("prepare", "deploy", "verify", "destroy")
    )
    parser.add_argument("--runtime-dir", type=Path, default=RUNTIME_DIR)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--decoys", type=int, default=5)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()

    try:
        if args.action == "prepare":
            seed = args.seed if args.seed is not None else secrets.randbits(63)
            scenario = prepare(
                seed,
                args.decoys,
                quiz_scenario.parse_networks(args.exclude),
                args.runtime_dir,
            )
            print(
                f"[PASS] Prepared {scenario['scenario_id']} in "
                f"{scenario['authorized_cidr']} with {len(scenario['decoys'])} decoys"
            )
        elif args.action == "deploy":
            scenario = deploy(args.runtime_dir)
            print(
                f"[PASS] Deployed {scenario['scenario_id']} with "
                f"{len(scenario['decoys'])} decoys; private answer data was not displayed"
            )
        elif args.action == "verify":
            result = verify(args.runtime_dir)
            print(
                f"[PASS] Verified {result['services']} services and "
                f"{result['routes']} expected routes from the isolated attacker"
            )
        else:
            destroy(args.runtime_dir)
            print("[PASS] Destroyed the quiz range and deleted its private runtime files")
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
