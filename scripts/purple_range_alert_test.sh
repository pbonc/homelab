#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
alertmanager_url="${ALERTMANAGER_URL:-http://192.168.1.23:9093}"
ntfy_url="${NTFY_URL:-http://192.168.1.23:8093}"
subscriber_password_file="${root}/docker/ntfy/secrets/subscriber_password.txt"
topic="homelab-alerts"

if [[ ! -s "${subscriber_password_file}" ]]; then
  echo "[FAIL] Missing subscriber password; run make ntfy-secrets" >&2
  exit 1
fi

test_id="$(date --utc +%Y%m%dT%H%M%SZ)-$$"
started_epoch="$(date --utc +%s)"
started_at="$(date --utc +%Y-%m-%dT%H:%M:%SZ)"
purple_marker="purple-suppressed-${test_id}"
production_marker="production-delivered-${test_id}"

post_alerts() {
  local ends_at="${1:-}"
  local ending=""
  if [[ -n "${ends_at}" ]]; then
    ending=",\"endsAt\":\"${ends_at}\""
  fi

  local payload
  payload="$(
    printf '[
      {"labels":{"alertname":"HomelabNotificationTest","severity":"info","service":"purple-range-routing-test","instance":"brain","environment":"purple_range","expected_vulnerable":"true","notification_policy":"never"},"annotations":{"summary":"%s"},"startsAt":"%s"%s,"generatorURL":"http://192.168.1.23:9090"},
      {"labels":{"alertname":"HomelabNotificationTest","severity":"info","service":"production-routing-control","instance":"brain","environment":"production"},"annotations":{"summary":"%s"},"startsAt":"%s"%s,"generatorURL":"http://192.168.1.23:9090"}
    ]' \
      "${purple_marker}" "${started_at}" "${ending}" \
      "${production_marker}" "${started_at}" "${ending}"
  )"

  curl \
    --fail \
    --silent \
    --show-error \
    --header "Content-Type: application/json" \
    --data "${payload}" \
    "${alertmanager_url}/api/v2/alerts"
}

resolved=false
resolve_alerts() {
  if [[ "${resolved}" == false ]]; then
    resolved=true
    post_alerts "$(date --utc +%Y-%m-%dT%H:%M:%SZ)" || true
  fi
}
trap resolve_alerts EXIT HUP INT TERM

post_alerts
echo "[INFO] Submitted one suppressed range alert and one production control alert"
sleep 15

messages="$(
  curl \
    --fail \
    --silent \
    --show-error \
    --user "homelab-iphone:$(<"${subscriber_password_file}")" \
    "${ntfy_url}/${topic}/json?poll=1&since=${started_epoch}"
)"

if grep --fixed-strings --quiet "${purple_marker}" <<<"${messages}"; then
  echo "[FAIL] Purple-Team alert reached ntfy despite notification_policy=never" >&2
  exit 1
fi

if ! grep --fixed-strings --quiet "${production_marker}" <<<"${messages}"; then
  echo "[FAIL] Production control alert did not reach the ntfy cache" >&2
  exit 1
fi

resolve_alerts
trap - EXIT HUP INT TERM

echo "[PASS] Purple-Team alert was discarded and production control reached ntfy"
echo "[INFO] Both synthetic alerts were resolved"
