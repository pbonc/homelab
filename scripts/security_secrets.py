#!/usr/bin/env python3
"""Create ignored security-status configuration without printing credentials."""

from __future__ import annotations

import getpass
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docker" / "security-status"


def write_secret(path: Path, prompt: str) -> None:
    if path.exists():
        print(f"[SKIP] Secret already exists: {path.name}")
        return
    value = getpass.getpass(prompt).strip()
    if not value:
        raise SystemExit(f"[FAIL] {path.name} must not be empty")
    path.write_text(value + "\n", encoding="utf-8")
    # Compose file-backed secrets retain host permissions. The 0700 parent
    # protects host traversal while the non-root container can read the file.
    path.chmod(0o644)
    print(f"[PASS] Created secret: {path.name}")


def main() -> int:
    env_path = ROOT / ".env"
    if env_path.exists():
        print("[SKIP] Runtime configuration already exists: .env")
    else:
        shutil.copyfile(ROOT / ".env.example", env_path)
        env_path.chmod(0o600)
        print("[PASS] Created runtime configuration: .env")

    secret_root = ROOT / "secrets"
    secret_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    secret_root.chmod(0o700)
    write_secret(secret_root / "aikido_client_id.txt", "Aikido client ID: ")
    write_secret(secret_root / "aikido_client_secret.txt", "Aikido client secret: ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
