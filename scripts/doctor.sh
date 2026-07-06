#!/usr/bin/env bash

set -u

EXPECTED_HOSTNAME="brain"

pass() {
  echo "[PASS] $1"
}

warn() {
  echo "[WARN] $1"
}

info() {
  echo "[INFO] $1"
}

check_required_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    pass "$cmd is installed"
  else
    warn "$cmd is not installed (required)"
  fi
}

check_optional_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    pass "$cmd is installed"
  else
    info "$cmd is not installed yet (optional at this stage)"
  fi
}

echo "== Homelab Doctor =="
echo

echo "-- Hostname --"
current_hostname="$(hostname)"
if [[ "$current_hostname" == "$EXPECTED_HOSTNAME" ]]; then
  pass "Hostname is $current_hostname"
else
  warn "Hostname is $current_hostname (expected: $EXPECTED_HOSTNAME)"
fi

echo
echo "-- OS Version --"
if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  pass "OS: ${PRETTY_NAME:-unknown}"
else
  warn "/etc/os-release not found"
fi

echo
echo "-- Disk Space --"
if command -v df >/dev/null 2>&1; then
  root_disk="$(df -h / | tail -n 1)"
  pass "Root filesystem: $root_disk"
else
  warn "df command unavailable"
fi

echo
echo "-- Memory --"
if command -v free >/dev/null 2>&1; then
  mem_line="$(free -h | awk '/^Mem:/ {print $0}')"
  pass "$mem_line"
else
  warn "free command unavailable"
fi

echo
echo "-- CPU --"
if command -v lscpu >/dev/null 2>&1; then
  cpu_model="$(lscpu | awk -F: '/Model name/ {gsub(/^ +/, "", $2); print $2; exit}')"
  cpu_count="$(nproc 2>/dev/null || echo "unknown")"
  pass "CPU: ${cpu_model:-unknown} | Cores: $cpu_count"
else
  warn "lscpu command unavailable"
fi

echo
echo "-- Required Tooling --"
check_required_cmd git
check_required_cmd make
check_required_cmd python3

echo
echo "-- Optional Tooling (planned) --"
check_optional_cmd docker
check_optional_cmd ansible
check_optional_cmd terraform

echo
echo "Doctor checks complete."
