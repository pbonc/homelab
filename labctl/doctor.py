from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

EXPECTED_HOSTNAME = "brain"


def _pass(message: str) -> None:
    print(f"[PASS] {message}")


def _warn(message: str) -> None:
    print(f"[WARN] {message}")


def _info(message: str) -> None:
    print(f"[INFO] {message}")


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _check_required_cmd(cmd: str) -> None:
    if _which(cmd):
        _pass(f"{cmd} is installed")
    else:
        _warn(f"{cmd} is not installed (required)")


def _check_optional_cmd(cmd: str) -> None:
    if _which(cmd):
        _pass(f"{cmd} is installed")
    else:
        _info(f"{cmd} is not installed yet (optional at this stage)")


def run_doctor() -> int:
    print("== Homelab Doctor ==")
    print()

    print("-- Hostname --")
    current_hostname = socket.gethostname()
    if current_hostname == EXPECTED_HOSTNAME:
        _pass(f"Hostname is {current_hostname}")
    else:
        _warn(f"Hostname is {current_hostname} (expected: {EXPECTED_HOSTNAME})")

    print()
    print("-- OS Version --")
    os_release = Path("/etc/os-release")
    if os_release.exists():
        pretty_name = "unknown"
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                pretty_name = line.split("=", 1)[1].strip().strip('"') or "unknown"
                break
        _pass(f"OS: {pretty_name}")
    else:
        _warn("/etc/os-release not found")

    print()
    print("-- Disk Space --")
    if _which("df"):
        output = _run(["df", "-h", "/"])
        lines = output.splitlines()
        root_disk = lines[-1] if lines else "unknown"
        _pass(f"Root filesystem: {root_disk}")
    else:
        _warn("df command unavailable")

    print()
    print("-- Memory --")
    if _which("free"):
        output = _run(["free", "-h"])
        mem_line = "unknown"
        for line in output.splitlines():
            if line.startswith("Mem:"):
                mem_line = line
                break
        _pass(mem_line)
    else:
        _warn("free command unavailable")

    print()
    print("-- CPU --")
    if _which("lscpu"):
        cpu_model = "unknown"
        output = _run(["lscpu"])
        for line in output.splitlines():
            if line.startswith("Model name"):
                cpu_model = line.split(":", 1)[1].strip() or "unknown"
                break

        cpu_count = "unknown"
        if _which("nproc"):
            maybe_count = _run(["nproc"])
            if maybe_count:
                cpu_count = maybe_count

        _pass(f"CPU: {cpu_model} | Cores: {cpu_count}")
    else:
        _warn("lscpu command unavailable")

    print()
    print("-- Required Tooling --")
    _check_required_cmd("git")
    _check_required_cmd("make")
    _check_required_cmd("python3")

    print()
    print("-- Optional Tooling (planned) --")
    _check_optional_cmd("docker")
    _check_optional_cmd("ansible")
    _check_optional_cmd("terraform")

    print()
    print("Doctor checks complete.")
    return 0
