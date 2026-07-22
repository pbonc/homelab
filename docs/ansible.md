# Ansible Node Automation

## Connection model

The production inventory lives in
`ansible/inventories/production/hosts.yml`. `brain` is the controller node and
`piaware` is the first active edge node. Future nodes remain absent until their
hostname, address, and SSH identity have been verified.

Run Ansible from a Linux control environment: `brain`, a Linux workstation, or
WSL. Native Windows is not an Ansible control-node target. Managed nodes require
SSH, a POSIX shell, and Python; they do not need Ansible installed.

Connections use the inventory's SSH user and the operator's SSH agent or normal
OpenSSH key discovery. Private-key paths, passwords, tokens, and vault passwords
must not be committed. Host-key checking remains enabled.

## Install the control tooling

Use a dedicated virtual environment so Ansible does not modify the host Python
installation:

```bash
python3 -m venv .venv-ansible
. .venv-ansible/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install ansible-core
```

Before the first Ansible run, establish and verify the SSH trust relationship:

```bash
ssh dar@192.168.1.23 'hostname; id'
ssh pi@192.168.1.27 'hostname; id'
```

Confirm that the returned hostnames are `brain` and `piaware`, respectively,
and verify an unexpected host-key prompt out of band. Do not bypass host-key
checking. The `pi` account is the PiAware image's initial administrative
identity; Phase 7 automation will replace it as the routine operator account.

## Validate connectivity

From the repository root:

```bash
make ansible-inventory
make ansible-ping
make ansible-check
```

`ansible-inventory` shows the effective target graph. `ansible-ping` verifies
SSH and Python. `ansible-check` runs the read-only connectivity playbook in
check mode. None of these commands uses privilege escalation or changes the
managed node.

To use a non-default key without storing its path in Git, load it into
`ssh-agent` or set `ANSIBLE_PRIVATE_KEY_FILE` for the current shell.

## Adding a node

1. Record its role, hostname, reserved LAN address, and owner in
   `docs/network.md`.
2. Install the operator public key and verify the SSH host fingerprint.
3. Add the host beneath the appropriate inventory group. Do not add an
   unverified placeholder.
4. Run the three validation commands above with `--limit <hostname>` appended
   to the underlying Ansible command when testing a single new node.
5. Only apply a mutating playbook after its check-mode output has been reviewed.

Non-secret shared values belong in `group_vars`. Secret handling is a separate
Phase 7 deliverable; until it is implemented, secrets remain runtime-only and
must not be added to inventory files.
