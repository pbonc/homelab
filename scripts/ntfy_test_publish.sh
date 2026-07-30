#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
password_file="${root}/docker/ntfy/secrets/publisher_password.txt"

if [[ ! -s "${password_file}" ]]; then
  echo "[FAIL] Missing publisher password; run make ntfy-secrets" >&2
  exit 1
fi

curl \
  --fail \
  --silent \
  --show-error \
  --user "homelab-publisher:$(<"${password_file}")" \
  --header "Title: Homelab notification test" \
  --header "Priority: default" \
  --header "Tags: white_check_mark" \
  --data "Authenticated LAN-only delivery from brain is working." \
  "http://192.168.1.23:8093/homelab-alerts"

echo "[PASS] Published authenticated test notification"
