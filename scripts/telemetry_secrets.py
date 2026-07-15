#!/usr/bin/env python3
"""Create local telemetry configuration and secrets without overwriting them."""

from __future__ import annotations

import secrets
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docker" / "telemetry"
SECRET_FILES = (
    "influxdb_admin_password.txt",
    "influxdb_admin_token.txt",
    "grafana_admin_password.txt",
)


def main() -> int:
    environment = ROOT / ".env"
    if not environment.exists():
        shutil.copy2(ROOT / ".env.example", environment)
        print(f"[PASS] Created {environment.relative_to(ROOT.parents[1])}")
    else:
        print(f"[SKIP] {environment.relative_to(ROOT.parents[1])} already exists")

    secret_root = ROOT / "secrets"
    secret_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    for filename in SECRET_FILES:
        path = secret_root / filename
        if path.exists():
            print(f"[SKIP] Secret already exists: {filename}")
            continue
        path.write_text(secrets.token_urlsafe(48) + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        print(f"[PASS] Created secret: {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
