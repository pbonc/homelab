from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import random
import secrets
from collections.abc import Iterable


SCHEMA_VERSION = "1.0.0"
QUIZ_TYPES = ("idor", "sql_injection", "stored_xss")
QUIZ_TEMPLATES = {
    "idor": "expense-idor",
    "sql_injection": "inventory-sqli",
    "stored_xss": "guestbook-stored-xss",
}
RANGE_POOL = ipaddress.ip_network("172.29.0.0/16")
SCENARIO_PREFIX = 27


def parse_networks(values: Iterable[str]) -> list[ipaddress.IPv4Network]:
    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        network = ipaddress.ip_network(value, strict=False)
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError("quiz range supports IPv4 networks only")
        networks.append(network)
    return networks


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
    hosts = list(subnet.hosts())
    selected = rng.sample(hosts, decoy_count + 1)
    target_address = selected[0]
    decoys = sorted(str(address) for address in selected[1:])
    quiz_type = rng.choice(QUIZ_TYPES)
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
    scenario = generate_scenario(
        seed=seed,
        excluded=parse_networks(args.exclude),
        decoy_count=args.decoys,
    )
    print(json.dumps(scenario, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
