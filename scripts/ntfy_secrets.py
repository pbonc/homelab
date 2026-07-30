#!/usr/bin/env python3
"""Create ignored ntfy credentials and declarative bcrypt configuration."""

from __future__ import annotations

import getpass
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NTFY_ROOT = ROOT / "docker" / "ntfy"
SECRETS_ROOT = NTFY_ROOT / "secrets"
IMAGE = (
    "binwiederhier/ntfy@"
    "sha256:081b53dbb20674fcfe05fdb4eb8af9036a2645ef979543d16f7f80803af467b1"
)
TOPIC = "homelab-alerts"
HASH_PATTERN = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")


def prompt_password(label: str) -> str:
    first = getpass.getpass(f"{label} password: ")
    second = getpass.getpass(f"Confirm {label.lower()} password: ")
    if not first or first != second:
        raise SystemExit("[FAIL] Passwords must be non-empty and match")
    if "\n" in first or "\r" in first:
        raise SystemExit("[FAIL] Passwords cannot contain line breaks")
    return first


def hash_password(password: str) -> str:
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", IMAGE, "user", "hash"],
            input=f"{password}\n{password}\n",
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError as error:
        raise SystemExit("[FAIL] Docker is required to hash ntfy passwords") from error

    match = HASH_PATTERN.search(result.stdout + "\n" + result.stderr)
    if result.returncode != 0 or match is None:
        raise SystemExit(
            "[FAIL] ntfy could not hash the password. Ensure Docker is running "
            "and the pinned image can be pulled."
        )
    return match.group(0)


def write_private(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    env_path = NTFY_ROOT / ".env"
    if env_path.exists():
        print("[SKIP] ntfy credentials already exist; remove .env and secrets to rotate")
        return 0

    publisher_password = prompt_password("Publisher")
    subscriber_password = prompt_password("iPhone subscriber")
    publisher_hash = hash_password(publisher_password)
    subscriber_hash = hash_password(subscriber_password)
    # Compose performs dollar interpolation on values read from .env. Doubling
    # dollars preserves the literal bcrypt hash delivered to the container.
    publisher_hash = publisher_hash.replace("$", "$$")
    subscriber_hash = subscriber_hash.replace("$", "$$")

    SECRETS_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    SECRETS_ROOT.chmod(0o700)
    write_private(SECRETS_ROOT / "publisher_password.txt", publisher_password)
    write_private(SECRETS_ROOT / "subscriber_password.txt", subscriber_password)

    env = (
        f"NTFY_AUTH_USERS=homelab-publisher:{publisher_hash}:user,"
        f"homelab-iphone:{subscriber_hash}:user\n"
        f"NTFY_AUTH_ACCESS=homelab-publisher:{TOPIC}:wo,"
        f"homelab-iphone:{TOPIC}:ro\n"
    )
    write_private(env_path, env.rstrip("\n"))

    print("[PASS] Created ntfy publisher and read-only iPhone subscriber")
    print(f"[PASS] Topic: {TOPIC}")
    print("[PASS] Credentials are stored in docker/ntfy/secrets (ignored by Git)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
