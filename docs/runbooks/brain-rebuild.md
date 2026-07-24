# Disposable Brain Rebuild Exercise

## Purpose and safety boundary

This exercise proves that a clean Ubuntu environment can be prepared from the
Git repository and encrypted backups without modifying production `brain`.
The target is a disposable WSL2 distribution named `Homelab-Rebuild-Lab`.

The exercise must never target hostname `brain` or address `192.168.1.23`.
The rebuild playbook also requires:

- inventory host `rebuild-lab`;
- environment `rebuild`;
- marker `/etc/homelab-rebuild-lab`;
- a hostname other than `brain`;
- an address other than `192.168.1.23`.

WSL is a controller-recovery rehearsal, not proof of bare-metal drivers,
firmware, LAN addressing, physical-disk replacement, or a host-managed NTP
daemon. WSL2 receives clock synchronization from Windows, so this inventory
skips time-service management while still applying the production timezone.

## 1. Create the disposable Ubuntu target

From PowerShell, list the current distributions and install a separately named
Ubuntu instance:

```powershell
wsl --list --verbose
wsl --install Ubuntu `
  --name Homelab-Rebuild-Lab `
  --web-download
```

Complete Ubuntu's first-run user creation. Do not name the distribution
`Ubuntu`, change the default distribution, or unregister the existing
production control environment.

Current Ubuntu WSL installations use systemd by default. Verify it inside the
new distribution:

```bash
ps -p 1 -o comm=
systemctl is-system-running
```

`systemctl is-system-running` may report `degraded` in WSL while still providing
the service manager required by this exercise. PID 1 must be `systemd`.

## 2. Mark and prepare the target

Inside `Homelab-Rebuild-Lab`, create the explicit safety marker and install only
the controller prerequisites:

```bash
printf '%s\n' 'disposable homelab controller rebuild target' |
  sudo tee /etc/homelab-rebuild-lab >/dev/null
sudo chmod 0644 /etc/homelab-rebuild-lab

sudo apt update
sudo apt install -y ansible-core make restic
```

Ansible's local WSL connection has no interactive terminal and cannot reuse the
terminal-bound sudo password cache. Grant the disposable bootstrap user
temporary non-interactive sudo, validate it, and leave it in place only through
the second check-mode run:

```bash
printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$USER" |
  sudo tee /etc/sudoers.d/99-homelab-rebuild-bootstrap >/dev/null
sudo chmod 0440 /etc/sudoers.d/99-homelab-rebuild-bootstrap
sudo visudo -cf /etc/sudoers.d/99-homelab-rebuild-bootstrap
```

This exception is permitted only because the entire distribution is disposable,
marked, and prohibited from targeting production. Never install this file on
`brain` or another persistent node.

Use the Windows-mounted Git checkout; do not clone secrets or copy production
volumes:

```bash
cd /mnt/c/dev/homelab
export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"
export HOMELAB_ADMIN_PUBLIC_KEY="$(
  tr -d '\r\n' </mnt/c/Users/darji/.ssh/id_ed25519_homelab.pub
)"
```

These exports are intentionally session-only. Repeat them after exiting and
re-entering `Homelab-Rebuild-Lab`; the input assertion refuses to proceed when
the public key is absent.

## 3. Preview, apply, and prove idempotence

Run syntax validation and check mode before making target-local changes:

```bash
make rebuild-syntax
make rebuild-check
```

Review the diff. It must name only `rebuild-lab`. Then apply and repeat check
mode:

```bash
make rebuild-apply
make rebuild-check
```

The second check-mode recap must report `changed=0`. Verify the baseline:

```bash
id dar
sudo -u dar sudo -n true
systemctl is-active docker
sudo -iu dar docker version
timedatectl show --property=Timezone --value
```

After evidence collection, remove the temporary bootstrap privilege and verify
that the managed `dar` account retains its separately declared sudo access:

```bash
sudo -u dar sudo -n true
sudo rm /etc/sudoers.d/99-homelab-rebuild-bootstrap
```

## 4. Restore into staging only

Create a disposable Restic password file from the password-manager copy. Never
paste the password into a command line, transcript, Git file, or Windows-backed
directory:

Restic repository keys have opaque IDs rather than friendly names. The label
`Homelab Restic Repository` belongs in the password manager; Restic's
`key list` output will show only the corresponding key ID and creation metadata.

```bash
mkdir -p ~/.config/homelab-backup
chmod 0700 ~/.config/homelab-backup
read -rsp 'Restic repository password: ' password; echo
printf '%s\n' "$password" >~/.config/homelab-backup/restic-password
unset password
chmod 0600 ~/.config/homelab-backup/restic-password
```

Restore the latest snapshots to a target-local staging directory:

```bash
export RESTIC_REPOSITORY=/mnt/c/Users/darji/HomelabBackups/restic
export RESTIC_PASSWORD_FILE="$HOME/.config/homelab-backup/restic-password"
sudo install -d -o "$USER" -g "$USER" -m 0700 /srv/recovery-staging

restic restore latest --tag brain-runtime \
  --target /srv/recovery-staging/runtime
restic restore latest --tag influxdb \
  --target /srv/recovery-staging/influxdb
restic restore latest --tag study-deck \
  --target /srv/recovery-staging/study
```

List archives without extracting secrets into the Git checkout:

```bash
tar -tf /srv/recovery-staging/runtime/exports/brain/runtime.tar
tar -tf /srv/recovery-staging/influxdb/exports/brain/influxdb.tar
python3 -m json.tool \
  /srv/recovery-staging/study/exports/brain/study-progress.json >/dev/null
```

Reconstruct a temporary source tree, overlay the restored runtime files, and
validate every Compose model without starting a container:

```bash
make rebuild-stage-validate
```

The command requires the rebuild marker, refuses the production hostname and
address, checks Docker Compose v2, validates the InfluxDB archive and Study Deck
JSON, and removes its temporary plaintext tree on exit.

## 5. Validation and evidence

Record:

- Ubuntu and kernel versions;
- first apply and second check-mode recaps;
- Docker and time-synchronization status;
- Docker Engine and Compose v2 versions;
- snapshot IDs and restore completion;
- missing manual prerequisites or production-only assumptions;
- elapsed time against the documented RTOs.

Do not start Compose stacks unchanged in WSL. Several services deliberately bind
to production address `192.168.1.23`; validation needs temporary rebuild-only
overrides before runtime startup. Do not restore the GitHub Actions runner
identity into a disposable host.

## 6. Destruction

Copy only sanitized evidence into the repository. From PowerShell, verify the
exact disposable name before destruction:

```powershell
wsl --list --verbose
wsl --terminate Homelab-Rebuild-Lab
wsl --unregister Homelab-Rebuild-Lab
```

`wsl --unregister` permanently deletes that distribution. Never substitute
`Ubuntu`, which is the workstation control environment.

The roadmap item closes only after baseline idempotence, staged restore, and
rebuild-specific gaps are documented.

## Initial exercise evidence

The initial exercise completed on July 24, 2026 using a separately named Ubuntu
26.04 WSL2 distribution:

- production hostname and address assertions passed on every Ansible run;
- the first baseline apply completed with six expected changes;
- repeated check mode converged with `changed=0` and `failed=0`;
- managed user `dar` received the declared SSH key, sudo access, and Docker
  group membership;
- Docker Engine 29.1.3 and Compose 2.40.3 were validated as `dar`;
- the password-manager recovery key independently opened the Restic repository;
- Brain runtime, InfluxDB, and Study Deck snapshots restored into staging and
  passed archive or JSON validation;
- reconstructed source plus restored runtime files produced valid Compose models
  for Homepage, telemetry, security status, observability, and Study Deck;
- the temporary bootstrap sudo rule was scoped to the disposable target; final
  distribution destruction removed all staged plaintext;
- `Homelab-Rebuild-Lab` was unregistered while the workstation `Ubuntu`
  distribution remained installed.

The exercise exposed and corrected two declared-state gaps: WSL clock ownership
needed an explicit host-managed exception, and the Docker baseline needed to
install Compose v2 in addition to the engine. It also confirmed that production
LAN bindings and the GitHub Actions runner identity require separate
rebuild-time handling rather than blind restoration.
