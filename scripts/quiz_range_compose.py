from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
from typing import Any


TRAILHEAD_IMAGE = "homelab/trailhead-rentals:0.1.0"
DECOY_IMAGE = "homelab/vulnerability-quiz-decoy:0.1.0"
ATTACKER_IMAGE = "homelab/vulnerability-quiz-attacker:0.1.0"


def constrained_service(image: str, address: str) -> dict[str, Any]:
    return {
        "image": image,
        "read_only": True,
        "tmpfs": ["/tmp:size=8m,mode=1777"],
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "restart": "no",
        "mem_limit": "96m",
        "cpus": 0.25,
        "pids_limit": 64,
        "labels": {
            "environment": "purple_range",
            "notification_policy": "never",
        },
        "networks": {"quiz-range": {"ipv4_address": address}},
    }


def render_compose(scenario: dict[str, Any]) -> dict[str, Any]:
    subnet = ipaddress.ip_network(scenario["authorized_cidr"])
    if not isinstance(subnet, ipaddress.IPv4Network) or subnet.prefixlen != 27:
        raise ValueError("scenario must use an IPv4 /27")
    gateway = next(subnet.hosts())
    target = scenario["target"]
    addresses = [ipaddress.ip_address(target["address"])]
    addresses.extend(ipaddress.ip_address(item["address"]) for item in scenario["decoys"])
    if len(addresses) != len(set(addresses)):
        raise ValueError("target and decoy addresses must be unique")
    if gateway in addresses or any(address not in subnet for address in addresses):
        raise ValueError("service address is outside the usable scenario pool")

    target_service = constrained_service(TRAILHEAD_IMAGE, target["address"])
    target_service.update(
        {
            "environment": {"TRAILHEAD_VARIANT_SET": target["trailhead_variant_set"]},
            "expose": ["8080"],
            "healthcheck": {
                "test": [
                    "CMD",
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)",
                ],
                "interval": "15s",
                "timeout": "5s",
                "retries": 5,
                "start_period": "5s",
            },
        }
    )
    target_service["labels"]["expected_vulnerable"] = "true"

    attacker_service = constrained_service(ATTACKER_IMAGE, "")
    attacker_service.update(
        {
            "profiles": ["attacker"],
            "entrypoint": ["/bin/sh"],
            "command": ["-c", "sleep infinity"],
            "stdin_open": True,
            "tty": True,
        }
    )
    # Let Docker allocate the disposable toolbox address so the private
    # manifest remains the sole source of target and decoy identities.
    attacker_service["networks"] = ["quiz-range"]
    attacker_service["labels"]["expected_vulnerable"] = "false"

    services: dict[str, Any] = {
        "trailhead-target": target_service,
        "attacker": attacker_service,
    }
    for index, decoy in enumerate(scenario["decoys"], start=1):
        service = constrained_service(DECOY_IMAGE, decoy["address"])
        service.update(
            {
                "environment": {
                    "DECOY_PROFILE": decoy["profile_id"],
                    "DECOY_HOSTNAME": decoy["hostname"],
                    "DECOY_PORT": str(decoy["port"]),
                },
                "hostname": decoy["hostname"],
                "expose": [str(decoy["port"])],
                "healthcheck": {
                    "test": [
                        "CMD",
                        "python",
                        "-c",
                        "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['DECOY_PORT'] + '/health', timeout=3)",
                    ],
                    "interval": "15s",
                    "timeout": "5s",
                    "retries": 5,
                    "start_period": "5s",
                },
            }
        )
        service["labels"]["expected_vulnerable"] = "false"
        services[f"decoy-{index:02d}"] = service

    return {
        "name": f"range-{scenario['scenario_id']}",
        "services": services,
        "networks": {
            "quiz-range": {
                "internal": True,
                "labels": {
                    "homelab.range.authorization": "lab-owned-targets-only",
                    "homelab.range.internet-access": "denied",
                    "homelab.range.production-access": "denied",
                    "notification_policy": "never",
                },
                "ipam": {
                    "config": [
                        {"subnet": str(subnet), "gateway": str(gateway)}
                    ]
                },
            }
        },
    }


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a private quiz-range Compose model")
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    write_private_json(args.output, render_compose(scenario))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
