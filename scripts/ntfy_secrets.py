#!/usr/bin/env python3
"""Create ignored ntfy credentials and declarative bcrypt configuration."""

from __future__ import annotations

import getpass
import os
import re
import select
import subprocess
import time
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
    if os.name != "posix":
        raise SystemExit("[FAIL] Run make ntfy-secrets on the Linux host brain")

    # ntfy intentionally reads passwords from a terminal rather than stdin.
    # Give the pinned container a private pseudo-terminal and capture its
    # output without echoing either password or hash to the operator.
    import pty

    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "--interactive",
                "--tty",
                IMAGE,
                "user",
                "hash",
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
    except FileNotFoundError as error:
        os.close(master_fd)
        os.close(slave_fd)
        raise SystemExit("[FAIL] Docker is required to hash ntfy passwords") from error
    finally:
        if "process" in locals():
            os.close(slave_fd)

    output = bytearray()
    deadline = time.monotonic() + 180
    try:
        os.write(master_fd, f"{password}\r{password}\r".encode())
        while process.poll() is None and time.monotonic() < deadline:
            readable, _, _ = select.select([master_fd], [], [], 0.25)
            if readable:
                try:
                    output.extend(os.read(master_fd, 4096))
                except OSError:
                    break
        if process.poll() is None:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=min(5.0, remaining))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    finally:
        os.close(master_fd)

    decoded = output.decode("utf-8", errors="replace")
    match = HASH_PATTERN.search(decoded)
    if process.returncode != 0 or match is None:
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
