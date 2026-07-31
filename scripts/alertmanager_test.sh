#!/usr/bin/env bash
set -euo pipefail

alertmanager_url="${ALERTMANAGER_URL:-http://192.168.1.23:9093}"
started_at="$(date --utc +%Y-%m-%dT%H:%M:%SZ)"

firing_payload="$(
  printf \
    '[{"labels":{"alertname":"HomelabNotificationTest","severity":"info","service":"alertmanager-test","instance":"brain"},"annotations":{"summary":"Synthetic homelab notification-path test"},"startsAt":"%s","generatorURL":"http://192.168.1.23:9090"}]' \
    "${started_at}"
)"

curl \
  --fail \
  --silent \
  --show-error \
  --header "Content-Type: application/json" \
  --data "${firing_payload}" \
  "${alertmanager_url}/api/v2/alerts"

echo "[PASS] Synthetic alert is firing; waiting for ntfy delivery"
sleep 15

resolved_at="$(date --utc +%Y-%m-%dT%H:%M:%SZ)"
resolved_payload="$(
  printf \
    '[{"labels":{"alertname":"HomelabNotificationTest","severity":"info","service":"alertmanager-test","instance":"brain"},"annotations":{"summary":"Synthetic homelab notification-path test"},"startsAt":"%s","endsAt":"%s","generatorURL":"http://192.168.1.23:9090"}]' \
    "${started_at}" \
    "${resolved_at}"
)"

curl \
  --fail \
  --silent \
  --show-error \
  --header "Content-Type: application/json" \
  --data "${resolved_payload}" \
  "${alertmanager_url}/api/v2/alerts"

echo "[PASS] Synthetic alert resolved; the recovery notification may take 10 seconds"
