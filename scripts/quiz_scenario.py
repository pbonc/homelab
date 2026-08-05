from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import random
import secrets
import subprocess
from collections.abc import Iterable
from collections.abc import Callable
from typing import Any


SCHEMA_VERSION = "1.0.0"
QUIZ_TYPES = ("idor", "sql_injection", "stored_xss")
QUIZ_TEMPLATES = {
    "idor": "expense-idor",
    "sql_injection": "inventory-sqli",
    "stored_xss": "guestbook-stored-xss",
}
TRAILHEAD_VARIANT_SETS = {
    ("idor",): "lesson-idor",
    ("sql_injection",): "lesson-sqli",
    ("stored_xss",): "lesson-stored-xss",
    ("idor", "sql_injection"): "lesson-idor-sqli",
    ("idor", "stored_xss"): "lesson-idor-stored-xss",
    ("sql_injection", "stored_xss"): "lesson-sqli-stored-xss",
    ("idor", "sql_injection", "stored_xss"): "lesson-idor-sqli-stored-xss",
}
RANGE_POOL = ipaddress.ip_network("172.29.0.0/16")
SCENARIO_PREFIX = 27
DECOY_PROFILES = {
    "documentation": {
        "hostname_prefix": "field-manual",
        "ports": (8080, 8081),
        "expected_routes": ("/", "/guides", "/health"),
    },
    "status": {
        "hostname_prefix": "trail-status",
        "ports": (8080, 8090),
        "expected_routes": ("/", "/api/status", "/health"),
    },
    "marketing": {
        "hostname_prefix": "summit-weekends",
        "ports": (8000, 8080),
        "expected_routes": ("/", "/cabins", "/health"),
    },
    "inventory_api": {
        "hostname_prefix": "gear-stock",
        "ports": (8080, 8888),
        "expected_routes": ("/", "/api/inventory", "/health"),
    },
    "employee_login": {
        "hostname_prefix": "crew-access",
        "ports": (8000, 8080),
        "expected_routes": ("/", "/login", "/health"),
    },
    "maintenance": {
        "hostname_prefix": "service-bench",
        "ports": (8080, 8090),
        "expected_routes": ("/", "/work-orders", "/health"),
    },
    "secure_catalog": {
        "hostname_prefix": "outfitter-catalog",
        "ports": (8000, 8080, 8888),
        "expected_routes": ("/", "/api/catalog", "/health"),
    },
}


class DockerNetworkDiscoveryError(RuntimeError):
    """Raised when live Docker network exclusions cannot be established safely."""


def parse_networks(values: Iterable[str]) -> list[ipaddress.IPv4Network]:
    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        network = ipaddress.ip_network(value, strict=False)
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError("quiz range supports IPv4 networks only")
        networks.append(network)
    return networks


def discover_docker_networks(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[ipaddress.IPv4Network]:
    """Return IPv4 subnets from every live Docker network or fail closed."""
    try:
        listed = run(
            ["docker", "network", "ls", "--quiet"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        raise DockerNetworkDiscoveryError(
            "cannot list Docker networks; no scenario was generated"
        ) from exc

    if listed.returncode != 0:
        detail = listed.stderr.strip() or "Docker network listing failed"
        raise DockerNetworkDiscoveryError(f"{detail}; no scenario was generated")

    network_ids = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    if not network_ids:
        raise DockerNetworkDiscoveryError(
            "Docker returned no networks; no scenario was generated"
        )

    try:
        inspected = run(
            ["docker", "network", "inspect", *network_ids],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        raise DockerNetworkDiscoveryError(
            "cannot inspect Docker networks; no scenario was generated"
        ) from exc
    if inspected.returncode != 0:
        detail = inspected.stderr.strip() or "Docker network inspection failed"
        raise DockerNetworkDiscoveryError(f"{detail}; no scenario was generated")

    try:
        payload: Any = json.loads(inspected.stdout)
    except json.JSONDecodeError as exc:
        raise DockerNetworkDiscoveryError(
            "Docker network inspection returned invalid JSON; no scenario was generated"
        ) from exc

    if not isinstance(payload, list) or len(payload) != len(network_ids):
        raise DockerNetworkDiscoveryError(
            "Docker did not return every requested network; no scenario was generated"
        )

    discovered: list[ipaddress.IPv4Network] = []
    for network in payload:
        if not isinstance(network, dict):
            raise DockerNetworkDiscoveryError(
                "Docker returned an invalid network record; no scenario was generated"
            )
        ipam = network.get("IPAM")
        configs = ipam.get("Config") if isinstance(ipam, dict) else None
        if not isinstance(configs, list):
            raise DockerNetworkDiscoveryError(
                "Docker network IPAM data is incomplete; no scenario was generated"
            )
        for config in configs:
            if not isinstance(config, dict):
                raise DockerNetworkDiscoveryError(
                    "Docker network IPAM configuration is invalid; no scenario was generated"
                )
            value = config.get("Subnet")
            if value is None:
                continue
            try:
                subnet = ipaddress.ip_network(value, strict=False)
            except (TypeError, ValueError) as exc:
                raise DockerNetworkDiscoveryError(
                    "Docker returned an invalid network subnet; no scenario was generated"
                ) from exc
            if isinstance(subnet, ipaddress.IPv4Network):
                discovered.append(subnet)

    return sorted(set(discovered), key=lambda item: (int(item.network_address), item.prefixlen))


def allocate_subnet(
    rng: random.Random,
    excluded: Iterable[ipaddress.IPv4Network],
) -> ipaddress.IPv4Network:
    excluded_networks = list(excluded)
    candidates = [
        subnet
        for subnet in RANGE_POOL.subnets(new_prefix=SCENARIO_PREFIX)
        if not any(subnet.overlaps(blocked) for blocked in excluded_networks)
    ]
    if not candidates:
        raise ValueError("no non-overlapping quiz subnet is available")
    return rng.choice(candidates)


def generate_scenario(
    seed: int,
    excluded: Iterable[ipaddress.IPv4Network] = (),
    decoy_count: int = 5,
) -> dict[str, object]:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if not 3 <= decoy_count <= 8:
        raise ValueError("decoy count must be between 3 and 8")

    rng = random.Random(seed)
    subnet = allocate_subnet(rng, excluded)
    # Docker bridge networks normally reserve the first usable address as the
    # gateway. Keep it out of the seeded service pool to prevent collisions.
    hosts = list(subnet.hosts())[1:]
    selected = rng.sample(hosts, decoy_count + 1)
    target_address = selected[0]
    profile_ids = list(DECOY_PROFILES)
    rng.shuffle(profile_ids)
    decoys = []
    for index, address in enumerate(selected[1:]):
        profile_id = profile_ids[index % len(profile_ids)]
        profile = DECOY_PROFILES[profile_id]
        decoys.append(
            {
                "address": str(address),
                "profile_id": profile_id,
                "hostname": f"{profile['hostname_prefix']}-{index + 1:02d}",
                "port": rng.choice(profile["ports"]),
                "expected_routes": list(profile["expected_routes"]),
            }
        )
    decoys.sort(key=lambda item: ipaddress.ip_address(item["address"]))
    vulnerability_count = rng.randint(1, len(QUIZ_TYPES))
    selected_classes = set(rng.sample(QUIZ_TYPES, vulnerability_count))
    vulnerability_classes = tuple(
        item for item in QUIZ_TYPES if item in selected_classes
    )
    quiz_type = vulnerability_classes[0]
    identity = hashlib.sha256(
        f"{SCHEMA_VERSION}:{seed}:{subnet}:{quiz_type}".encode("utf-8")
    ).hexdigest()[:12]

    return {
        "schema_version": SCHEMA_VERSION,
        "scenario_id": f"quiz-{identity}",
        "seed": seed,
        "authorized_cidr": str(subnet),
        "notification_policy": "never",
        "target": {
            "address": str(target_address),
            "quiz_type": quiz_type,
            "template_id": QUIZ_TEMPLATES[quiz_type],
            "vulnerability_classes": list(vulnerability_classes),
            "template_ids": [QUIZ_TEMPLATES[item] for item in vulnerability_classes],
            "trailhead_variant_set": TRAILHEAD_VARIANT_SETS[vulnerability_classes],
        },
        "decoys": decoys,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic, isolated vulnerability quiz scenario"
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--decoys", type=int, default=5)
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbits(63)
    try:
        excluded = [*parse_networks(args.exclude), *discover_docker_networks()]
        scenario = generate_scenario(
            seed=seed,
            excluded=excluded,
            decoy_count=args.decoys,
        )
    except (DockerNetworkDiscoveryError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(scenario, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
