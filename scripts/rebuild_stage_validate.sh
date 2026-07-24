#!/usr/bin/env bash
set -euo pipefail

readonly repository_root="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &&
    pwd
)"
readonly recovery_root="/srv/recovery-staging"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

[[ -f /etc/homelab-rebuild-lab ]] ||
  fail "Disposable rebuild marker is absent"
[[ "$(hostname -s)" != "brain" ]] ||
  fail "Refusing to run on production hostname brain"
if ip -4 address show | grep -Fq "192.168.1.23"; then
  fail "Refusing to run on the production brain address"
fi

for command in docker git sudo tar; do
  command -v "${command}" >/dev/null ||
    fail "Required command is unavailable: ${command}"
done
docker compose version >/dev/null ||
  fail "Docker Compose v2 is unavailable"

runtime_archive="${recovery_root}/runtime/exports/brain/runtime.tar"
influx_archive="${recovery_root}/influxdb/exports/brain/influxdb.tar"
study_export="${recovery_root}/study/exports/brain/study-progress.json"
for path in "${runtime_archive}" "${influx_archive}" "${study_export}"; do
  [[ -f "${path}" ]] || fail "Required staged restore is absent: ${path}"
done

stage_root="$(sudo mktemp -d /srv/homelab-rebuild.XXXXXX)"
case "${stage_root}" in
  /srv/homelab-rebuild.*) ;;
  *) fail "Unsafe temporary rebuild path: ${stage_root}" ;;
esac
sudo chown "$(id -u):$(id -g)" "${stage_root}"

cleanup() {
  case "${stage_root}" in
    /srv/homelab-rebuild.*) sudo rm -rf -- "${stage_root}" ;;
    *) printf '[WARN] Refusing unsafe cleanup path: %s\n' "${stage_root}" >&2 ;;
  esac
}
trap cleanup EXIT

source_root="${stage_root}/source"
runtime_root="${stage_root}/runtime"
mkdir -p "${source_root}" "${runtime_root}"

git -C "${repository_root}" ls-files \
  --cached \
  --others \
  --exclude-standard \
  -z |
  tar \
    --null \
    --directory="${repository_root}" \
    --files-from=- \
    --create \
    --file=- |
  tar --extract --file=- --directory="${source_root}"

tar --extract --file="${runtime_archive}" --directory="${runtime_root}"
restored_repository="${runtime_root}/home/dar/git/homelab"

for relative_path in \
  docker/telemetry/.env \
  docker/telemetry/secrets \
  docker/security-status/.env \
  docker/security-status/secrets
do
  restored_path="${restored_repository}/${relative_path}"
  [[ -e "${restored_path}" ]] ||
    fail "Runtime backup is missing ${relative_path}"
  rm -rf -- "${source_root:?}/${relative_path}"
  mkdir -p "$(dirname -- "${source_root}/${relative_path}")"
  cp -a "${restored_path}" "${source_root}/${relative_path}"
done

tar -tf "${influx_archive}" >/dev/null
python3 -m json.tool "${study_export}" >/dev/null

(
  cd "${source_root}"
  docker compose \
    --env-file docker/telemetry/.env \
    --file docker/telemetry/compose.yaml \
    config --quiet
  docker compose \
    --env-file docker/security-status/.env \
    --file docker/security-status/compose.yaml \
    config --quiet
  docker compose \
    --file docker/observability/compose.yaml \
    config --quiet
  docker compose \
    --file docker/study-deck/compose.yaml \
    config --quiet
  docker compose \
    --file docker/homepage/compose.yaml \
    config --quiet
)

printf '[PASS] Reconstructed and validated all controller Compose models\n'
printf '[PASS] Validated staged InfluxDB and Study Deck recovery artifacts\n'
