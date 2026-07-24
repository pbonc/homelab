# Encrypted Off-Host Backups

## Architecture

Ubuntu WSL on the operator workstation pulls supported exports from `brain` and
`piaware` over key-authenticated SSH. Restic encrypts and authenticates every
object before writing its repository to:

`C:\Users\darji\HomelabBackups\restic`

Backblaze Computer Backup then copies that ordinary local directory off-site.
No plaintext database export, runtime secret, token, or PiAware feeder identity
is staged on the Backblaze-visible Windows filesystem. The optional USB NVMe is
a future disconnected copy of the already-encrypted Restic repository, not the
primary scheduled destination.

## State classification

| Data | Method | RPO | RTO | Reason |
| --- | --- | ---: | ---: | --- |
| InfluxDB telemetry and deployment events | Supported bucket-level `influx backup` export | 24 hours | 8 hours | Long-lived weather history and annotations |
| Study Deck progress | Versioned application export API | 24 hours | 4 hours | Personal learning history |
| Telemetry and security runtime configuration/secrets | Encrypted tar stream | 24 hours | 4 hours | Required to re-establish scoped service access |
| Homepage deployment-event journal and active metadata | Encrypted tar stream | 24 hours | 4 hours | Local deployment audit trail |
| PiAware configuration and feeder identity | Privileged encrypted tar stream | 24 hours | 4 hours | Preserves receiver identity and configuration |

Git-tracked source, provisioned dashboards, container images, Homepage release
copies, Prometheus metrics, Loki logs, and Alloy positions are rebuildable or
disposable. They are deliberately excluded from the irreplaceable-state set.

## Encryption and credentials

The Restic password file lives only in WSL at
`~/.config/homelab-backup/restic-password` with mode `0600`. Store a second copy
of that password in the operator password manager. Losing it makes every
snapshot unrecoverable. Never put the password file in the Restic repository,
the Git checkout, a managed node, or a terminal transcript.

InfluxDB's native backup API requires the root Operator token even when backing
up one bucket. The plaintext token in `influxdb_admin_token.txt` is therefore
retained as a recovery credential, mounted only into InfluxDB, and included only
inside the encrypted runtime snapshot. Collector and Grafana workloads continue
to use their independently scoped tokens.

The WSL controller uses `~/.ssh/id_ed25519_homelab`. The public key must be
authorized for `dar` on both managed nodes. Scheduled operation requires a
non-interactive key and non-interactive sudo only for the explicitly managed
PiAware administrator.

## Repository lifecycle

Install Restic in WSL and create the password file before initialization:

```bash
sudo apt update
sudo apt install -y restic
mkdir -p ~/.config/homelab-backup
chmod 0700 ~/.config/homelab-backup
read -rsp 'New Restic password: ' password; echo
printf '%s\n' "$password" > ~/.config/homelab-backup/restic-password
unset password
chmod 0600 ~/.config/homelab-backup/restic-password
```

Record the same password in the password manager, then initialize exactly once:

```bash
make backup-init
```

Routine commands are:

```bash
make backup-run
make backup-snapshots
make backup-check
make backup-restore-test
make backup-prune
```

Each run creates separate tagged snapshots for Brain runtime state, InfluxDB,
Study Deck progress, and PiAware configuration. It retains 7 daily, 5 weekly,
and 12 monthly snapshots. Routine runs expire snapshot metadata without pruning
pack files; `backup-prune` performs the heavier space-reclamation operation
during a deliberate maintenance window.

## Daily scheduling

Windows Task Scheduler starts WSL daily so Ubuntu does not need to remain open.
From a normal PowerShell session in the repository, register the task:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\install_backup_task.ps1
```

The default schedule is 03:00. Override it with `-Schedule HH:mm` if needed.
The task runs only in the signed-in Windows user's session, starts a missed run
when the workstation becomes available, refuses overlapping runs, and limits a
run to two hours. It writes its log inside WSL rather than the Restic repository:

```bash
tail -n 100 ~/.local/state/homelab-backup/backup.log
```

Test the registered task from PowerShell, then inspect that log:

```powershell
Start-ScheduledTask -TaskName "Homelab Daily Backup"
Get-ScheduledTaskInfo -TaskName "Homelab Daily Backup"
```

The dedicated SSH key must remain non-interactive, and the verified host keys
for both managed nodes must remain in WSL's `known_hosts`.

## Backblaze verification

After the first backup, open Backblaze Settings and confirm the local Restic
repository is not excluded. Confirm repository files appear in **Files
Scheduled for Backup**, wait for completion, and then verify them through
**View/Restore Files** in the Backblaze web console. Backblaze Personal Backup
is an active mirror with limited deleted-file history, so Restic—not Backblaze
version history—owns snapshot retention.

The external NVMe can hold a second encrypted repository copy, but standard
Backblaze retention requires selected external drives to reconnect regularly.
Do not make a usually disconnected disk the only local repository.

## Recovery objectives and proof

- Daily execution targets a 24-hour recovery point.
- Configuration, secrets, Study Deck state, and PiAware identity target a
  four-hour recovery time.
- InfluxDB targets an eight-hour recovery time because a full restore requires
  a compatible empty instance and its operator token.
- Run `backup-check` after every backup and a full repository prune monthly.
- Run `backup-restore-test` to restore every data class into a disposable WSL
  directory and validate its archive or JSON structure before declaring the
  backup roadmap complete. The command removes the plaintext test files when it
  exits.
- Perform a Backblaze-origin restore of repository files at least quarterly;
  a successful local Restic snapshot alone does not prove the off-site copy.

Initial proof was completed on July 24, 2026: the Windows scheduled task
finished with exit code `0`, every protected data class passed the disposable
restore test, and the encrypted Restic repository appeared in Backblaze's web
restore inventory.

InfluxDB restores must use the supported `influx restore` workflow against a
compatible instance and the retained Operator token. This repository contains a
native `telemetry` bucket export plus the metadata InfluxDB includes with it.
Never replace a live named volume with an unverified file copy.
