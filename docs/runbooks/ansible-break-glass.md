# Ansible and SSH Break-Glass Runbook

## Purpose and boundary

Use this runbook only when normal key-based SSH or Ansible access to a managed
homelab node fails. Recovery restores the declared access path; it is not a
shortcut for bypassing host-key verification or configuration review.

Never commit or paste private keys, passwords, vault passwords, or feeder IDs
into the repository, tickets, terminal transcripts, or screenshots. Preserve
an existing working shell until a second connection has been proven.

## Normal access contract

- Control environment: Ubuntu WSL on the operator workstation
- Inventory: `ansible/inventories/production/hosts.yml`
- Routine edge-node account: `dar`, public-key SSH
- PiAware recovery account: retained `pi` account with an operator-held password
- Privilege escalation: key-backed `dar` account with validated passwordless sudo
- Host-key checking: always enabled

## Triage before changing anything

From WSL, identify the failing layer:

```bash
ping -c 3 192.168.1.27
nc -vz 192.168.1.27 22
ssh -vv -i ~/.ssh/id_ed25519_homelab dar@192.168.1.27 true
```

Classify the result as network unreachable, SSH unavailable, host-key mismatch,
authentication failure, sudo failure, or Ansible/control-environment failure.
Do not alter the managed node when only the WSL virtual environment is broken.

## WSL or Ansible failure

Prove direct SSH first:

```bash
ssh -i ~/.ssh/id_ed25519_homelab dar@192.168.1.27 'hostname; id; sudo -n true'
```

If that works, repair or recreate only the disposable Ansible environment:

```bash
python3 -m venv ~/.venvs/ansible
source ~/.venvs/ansible/bin/activate
python3 -m pip install --upgrade pip ansible-core
cd /mnt/c/dev/homelab
export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"
```

Then run `ansible piaware -m ansible.builtin.ping` before any playbook.

## Host-key mismatch

A changed host key can indicate a legitimate reimage or an interception attempt.
Do not accept it or delete the old entry until the new fingerprint is verified
at the physical console:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
```

After comparing the complete fingerprint through that independent path, remove
only the obsolete entry and reconnect interactively:

```bash
ssh-keygen -R 192.168.1.27
ssh -i ~/.ssh/id_ed25519_homelab dar@192.168.1.27
```

Reject an unexplained mismatch and investigate the address assignment before
continuing.

## Restore the administrator key

If `dar` authentication fails but the retained `pi` recovery account works,
send only the public key from WSL and rebuild the declared file permissions:

```bash
cat ~/.ssh/id_ed25519_homelab.pub | \
  ssh pi@192.168.1.27 \
  'sudo install -d -o dar -g dar -m 0700 /home/dar/.ssh &&
   sudo tee /home/dar/.ssh/authorized_keys >/dev/null &&
   sudo chown dar:dar /home/dar/.ssh/authorized_keys &&
   sudo chmod 0600 /home/dar/.ssh/authorized_keys'
```

This intentionally replaces the damaged `dar` key file. Confirm the local
public-key fingerprint before using it, then prove a new `dar` session while
the recovery session remains open.

If remote recovery is unavailable, attach a keyboard and display to the Pi,
log in with the operator-held recovery credentials, and perform the same file
and permission repair locally. The repository does not contain that password.

## Repair sudo access

If `dar` can connect but `sudo -n true` fails, use the retained recovery account
or physical console. Validate the whole policy before editing:

```bash
sudo visudo -cf /etc/sudoers
sudo visudo -f /etc/sudoers.d/90-homelab-dar
```

The managed entry must grant the `dar` account `NOPASSWD: ALL`, be owned by
root, and have mode `0440`. Always use `visudo`; never redirect arbitrary text
directly into a sudoers file.

## Restore the SSH service or network

At the physical console, inspect before restarting:

```bash
ip -brief address
ip route
sudo systemctl status ssh --no-pager
sudo ss -lntp | grep ':22 '
sudo journalctl -u ssh -n 100 --no-pager
```

Correct the documented DHCP reservation or service configuration, validate it,
and then restart only the affected service. Do not reset networking or reimage
the node while PiAware data and configuration remain recoverable.

## Exit criteria

Recovery is complete only when all of the following pass from WSL:

```bash
ssh -o BatchMode=yes -i ~/.ssh/id_ed25519_homelab \
  dar@192.168.1.27 'hostname; sudo -n true; piaware-status'

ansible piaware -m ansible.builtin.ping \
  --private-key ~/.ssh/id_ed25519_homelab

make ansible-bootstrap-check \
  ARGS="--limit piaware --private-key $HOME/.ssh/id_ed25519_homelab"
```

The final check must report `changed=0`, `failed=0`, and `unreachable=0`.
Document the failure cause, manual actions, host-key decision, validation
results, and any automation gap. Close the recovery shell only after normal
access has been independently re-established.
