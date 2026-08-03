#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose --file docker/purple-range/compose.yaml)

cleanup() {
  "${compose[@]}" --profile attacker stop attacker >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[range] Validating Compose policy"
"${compose[@]}" config --quiet

echo "[range] Waiting for the target health contract"
for attempt in $(seq 1 30); do
  health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' purple-range-juice-shop 2>/dev/null || true)
  if [[ "$health" == "healthy" ]]; then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "[FAIL] Juice Shop did not become healthy" >&2
    exit 1
  fi
  sleep 2
done

echo "[range] Proving attacker-to-target connectivity"
"${compose[@]}" --profile attacker run --rm --no-deps attacker \
  -ec 'curl --fail --silent --show-error --max-time 5 http://juice-shop:3000/ >/dev/null'

echo "[range] Proving loopback-only browser ingress through the gateway"
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:3008/ >/dev/null

echo "[range] Proving the attacker cannot reach the controller LAN address"
if "${compose[@]}" --profile attacker run --rm --no-deps attacker \
  -ec 'curl --fail --silent --max-time 3 http://192.168.1.23:3000/ >/dev/null'; then
  echo "[FAIL] Attacker reached a production service" >&2
  exit 1
fi

echo "[range] Proving the attacker has no direct internet path"
if "${compose[@]}" --profile attacker run --rm --no-deps attacker \
  -ec 'curl --fail --silent --max-time 3 http://1.1.1.1/ >/dev/null'; then
  echo "[FAIL] Attacker reached the internet" >&2
  exit 1
fi

echo "[PASS] Range target is reachable; production and internet paths are denied"
