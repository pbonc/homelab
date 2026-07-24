#!/usr/bin/env bash
set -euo pipefail

readonly DEFAULT_REPOSITORY="/mnt/c/Users/darji/HomelabBackups/restic"
readonly DEFAULT_PASSWORD_FILE="${HOME}/.config/homelab-backup/restic-password"
readonly DEFAULT_IDENTITY_FILE="${HOME}/.ssh/id_ed25519_homelab"

RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-${DEFAULT_REPOSITORY}}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-${DEFAULT_PASSWORD_FILE}}"
HOMELAB_SSH_IDENTITY="${HOMELAB_SSH_IDENTITY:-${DEFAULT_IDENTITY_FILE}}"
BRAIN_SSH_TARGET="${BRAIN_SSH_TARGET:-dar@192.168.1.23}"
PIAWARE_SSH_TARGET="${PIAWARE_SSH_TARGET:-dar@192.168.1.27}"

export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE

ssh_command=(
  ssh
  -o BatchMode=yes
  -o ConnectTimeout=10
  -i "${HOMELAB_SSH_IDENTITY}"
)

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Required file not found: $1"
}

preflight() {
  command -v restic >/dev/null || fail "restic is not installed in WSL"
  command -v ssh >/dev/null || fail "ssh is not installed in WSL"
  require_file "${RESTIC_PASSWORD_FILE}"
  require_file "${HOMELAB_SSH_IDENTITY}"
  [[ "${RESTIC_REPOSITORY}" == /mnt/c/* ]] ||
    fail "RESTIC_REPOSITORY must be on the Windows-backed /mnt/c filesystem"
}

restore_test() {
  local restore_root
  restore_root="$(mktemp -d)"
  trap "rm -rf -- '${restore_root}'" EXIT

  restic restore latest --tag brain-runtime --target "${restore_root}/runtime"
  restic restore latest --tag influxdb --target "${restore_root}/influxdb"
  restic restore latest --tag study-deck --target "${restore_root}/study"
  restic restore latest --tag piaware --target "${restore_root}/piaware"

  tar -tf "${restore_root}/runtime/exports/brain/runtime.tar" >/dev/null
  tar -tf "${restore_root}/influxdb/exports/brain/influxdb.tar" >/dev/null
  python3 -m json.tool \
    "${restore_root}/study/exports/brain/study-progress.json" >/dev/null
  tar -tf \
    "${restore_root}/piaware/exports/piaware/configuration.tar" >/dev/null

  rm -rf -- "${restore_root}"
  trap - EXIT
  printf '[PASS] Restored and validated every homelab backup data class\n'
}

restic_stdin() {
  local filename="$1"
  local tag="$2"
  restic backup \
    --stdin \
    --stdin-filename "$filename" \
    --host homelab \
    --tag "$tag"
}

backup_brain_runtime() {
  "${ssh_command[@]}" "${BRAIN_SSH_TARGET}" 'bash -s' <<'REMOTE' |
set -euo pipefail
paths=()
for path in \
  home/dar/git/homelab/docker/telemetry/.env \
  home/dar/git/homelab/docker/telemetry/secrets \
  home/dar/git/homelab/docker/security-status/.env \
  home/dar/git/homelab/docker/security-status/secrets \
  srv/homelab/homepage/deployed.json \
  srv/homelab/homepage/deployment-events.jsonl
do
  [[ -e "/${path}" ]] && paths+=("${path}")
done
(( ${#paths[@]} > 0 )) || {
  printf 'No brain runtime paths were found\n' >&2
  exit 1
}
tar -C / -cf - "${paths[@]}"
REMOTE
    restic_stdin "exports/brain/runtime.tar" "brain-runtime"
}

backup_influxdb() {
  "${ssh_command[@]}" "${BRAIN_SSH_TARGET}" 'bash -s' <<'REMOTE' |
set -euo pipefail
container_path=/tmp/homelab-influx-backup
host_stage="$(mktemp -d)"
cleanup() {
  docker exec influxdb rm -rf "${container_path}" >/dev/null 2>&1 || true
  rm -rf "${host_stage}"
}
trap cleanup EXIT

docker exec influxdb rm -rf "${container_path}"
docker exec influxdb sh -eu -c '
  INFLUX_TOKEN="$(cat /run/secrets/influxdb_admin_token)"
  export INFLUX_TOKEN
  influx backup --bucket telemetry /tmp/homelab-influx-backup
' >&2
docker cp "influxdb:${container_path}" "${host_stage}/influxdb" >&2
tar -C "${host_stage}" -cf - influxdb
REMOTE
    restic_stdin "exports/brain/influxdb.tar" "influxdb"
}

backup_study_progress() {
  "${ssh_command[@]}" "${BRAIN_SSH_TARGET}" \
    'curl --fail --silent --show-error http://192.168.1.23:8020/api/progress/export' |
    restic_stdin "exports/brain/study-progress.json" "study-deck"
}

backup_piaware() {
  "${ssh_command[@]}" "${PIAWARE_SSH_TARGET}" 'sudo -n bash -s' <<'REMOTE' |
set -euo pipefail
paths=()
for path in \
  etc/piaware.conf \
  boot/piaware-config.txt \
  boot/firmware/piaware-config.txt \
  var/cache/piaware/feeder_id
do
  [[ -e "/${path}" ]] && paths+=("${path}")
done
(( ${#paths[@]} > 0 )) || {
  printf 'No PiAware configuration paths were found\n' >&2
  exit 1
}
tar -C / -cf - "${paths[@]}"
REMOTE
    restic_stdin "exports/piaware/configuration.tar" "piaware"
}

run_backup() {
  restic cat config >/dev/null
  backup_brain_runtime
  backup_influxdb
  backup_study_progress
  backup_piaware
  restic forget --keep-daily 7 --keep-weekly 5 --keep-monthly 12
  restic check --read-data-subset=5%
  printf '[PASS] Encrypted homelab backup and repository check completed\n'
}

usage() {
  printf \
    'Usage: %s {init|backup|check|snapshots|restore-test|prune}\n' \
    "${0##*/}" >&2
  exit 2
}

main() {
  local command="${1:-}"
  preflight
  case "${command}" in
    init)
      mkdir -p "${RESTIC_REPOSITORY}"
      restic init
      ;;
    backup)
      run_backup
      ;;
    check)
      restic check --read-data-subset=5%
      ;;
    snapshots)
      restic snapshots
      ;;
    restore-test)
      restore_test
      ;;
    prune)
      restic forget --keep-daily 7 --keep-weekly 5 --keep-monthly 12 --prune
      ;;
    *)
      usage
      ;;
  esac
}

main "$@"
