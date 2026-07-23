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
checking. The `pi` account was the PiAware image's initial bootstrap identity;
inventory now uses the automation-managed `dar` account for routine access.

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

Non-secret shared values belong in committed `group_vars`; secrets must never
be added to those plaintext inventory files.

## Variable and secret boundaries

Ansible inputs use three deliberately separate classes:

1. Committed non-secret defaults live in `group_vars`, `host_vars`, and role
   defaults. Hostnames, ports, package names, service providers, and feature
   switches belong here.
2. Persistent secrets live only in the ignored production vault at
   `ansible/inventories/production/group_vars/all/vault.yml`. Secret variable
   names use the `vault_` prefix. The vault password belongs in the operator's
   password manager, never in the repository or on a managed node.
3. Ephemeral inputs are supplied through the control-shell environment. The
   administrator public key uses this path so the repository stays reusable,
   even though the public half is not itself secret.

Create the encrypted vault directly—never create a plaintext file and encrypt
it afterward:

```bash
make ansible-vault-create
```

The example at `ansible/examples/vault-variables.yml.example` documents naming
only. Enter real values in the encrypted editor. Later changes use:

```bash
make ansible-vault-edit
make ansible-vault-view
```

For playbook execution, let Ansible prompt for the vault password with
`--ask-vault-pass`, or point `ANSIBLE_VAULT_PASSWORD_FILE` at an operator-owned
file outside the repository. Do not pass secrets as command-line extra vars,
where shell history and process inspection can expose them.

## Bootstrap an edge node

The `node_baseline` role creates the `dar` administrator, installs its public
key, configures the `America/Chicago` timezone and system time synchronization,
and installs a small base package set. Docker is opt-in and remains disabled on
PiAware because its receiver stack does not require it.

Time synchronization is provider-aware. The PiAware host explicitly retains
its image-managed `ntpsec` service; the role does not install
`systemd-timesyncd`, because those packages conflict and replacing the provider
would remove PiAware release ownership. Every future node must select an
already-installed provider deliberately.

The administrator receives passwordless sudo backed by its SSH key. This avoids
putting a reusable password or password hash into Git and allows subsequent
non-interactive automation. Possession of the private administrative key is
therefore equivalent to root access; keep it encrypted and off managed nodes.

The role never reads a private key or commits a public key. In the Linux/WSL
control shell, export the public half of the dedicated homelab key:

```bash
export HOMELAB_ADMIN_PUBLIC_KEY="$(cat ~/.ssh/id_ed25519_homelab.pub)"
```

The role trims Windows or Unix line endings and reconciles the key by algorithm
and key body, preventing CRLF input or comment changes from creating duplicate
authorized-key entries.

Preview the first run while connecting through the PiAware image's temporary
`pi` account. `sudo` requests the changed Pi password:

```bash
make ansible-bootstrap-check ARGS="--limit piaware --ask-become-pass"
```

Review every proposed change, then apply the identical target selection:

```bash
make ansible-bootstrap ARGS="--limit piaware --ask-become-pass"
```

On the first preview, creation of the administrator is reported but its `.ssh`
directory and authorized key are explicitly deferred because check mode does
not actually create the account. The apply run creates them together. A second
check-mode run must then report no changes; that is the idempotence proof.

Before changing inventory or SSH policy, prove the new identity from the
control environment:

```bash
ssh -i ~/.ssh/id_ed25519_homelab dar@192.168.1.27 'hostname; id; sudo -n true; timedatectl'
```

The role deliberately does not disable the `pi` account or password-based SSH.
Those changes require a separate access-hardening step after the new identity,
sudo path, and a documented break-glass method have all been verified.

After the first successful apply and identity verification, inventory connects
as `dar`. Prove idempotence without a become-password prompt:

```bash
make ansible-bootstrap-check \
  ARGS="--limit piaware --private-key $HOME/.ssh/id_ed25519_homelab"
```

The PiAware baseline was applied and verified from the WSL control environment:
the apply and subsequent check-mode run both completed with `changed=0`,
`failed=0`, and `unreachable=0`. PiAware, `dump1090-fa`, `ntpsec`, key-based
administration, and passwordless sudo remained healthy after convergence.
