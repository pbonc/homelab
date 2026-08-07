# Isolated Purple-Team Range

## Purpose and authorization

The range exists for defensive learning against deliberately vulnerable,
lab-owned targets. Authorization covers only containers attached to the
`homelab-purple-range-target` network. It does not cover `brain`, `piaware`,
other trusted-LAN devices, public systems, or third-party services.

The first target is OWASP Juice Shop 20.0.0, an intentionally insecure training
application. Its image is pinned to the verified Linux AMD64 manifest digest.
The target is never published to all host interfaces: Docker binds it only to
`127.0.0.1:3008` on the range host through a constrained reverse-proxy
gateway. Juice Shop itself remains attached only to the internal target
network.

## Threat model

The primary hazard is that a deliberately vulnerable target or attacker tool
could reach production services, the trusted LAN, or the internet. Secondary
hazards are persistent compromised state, accidental long-running exposure,
resource exhaustion, and reuse of production credentials.

The first slice applies these controls:

- a dedicated Docker network with `internal: true`;
- a loopback-only target port rather than a LAN listener;
- a narrow reverse proxy that is the only service connected to both the
  loopback ingress network and the internal target network;
- no connection to any production Compose network;
- digest-pinned Linux AMD64 images;
- an attacker profile that is off by default and disposable;
- dropped Linux capabilities, disabled privilege escalation, and resource
  limits;
- no production secrets, volumes, sockets, or service accounts; and
- positive target-connectivity plus negative production and internet tests.

The Juice Shop filesystem is intentionally disposable. Do not add a persistent
volume. Resetting the target removes the container and creates a known-clean
instance from the pinned image.

## Lifecycle

Validate the static contract without starting anything:

```bash
make purple-range-test
make purple-range-config
```

Start the target:

```bash
make purple-range-up
```

From the range host, open `http://127.0.0.1:3008`. From another trusted
workstation, use an SSH local-forward instead of publishing Juice Shop to the
LAN:

```bash
ssh -N -L 3008:127.0.0.1:3008 dar@192.168.1.23
```

Then open `http://127.0.0.1:3008` on the workstation. The forwarding session
must remain open while using the target.

Homepage's **Juice Shop Lab** card opens the LAN-safe Purple-Team Range Portal
at `http://192.168.1.23:8050`. The portal provides copyable commands, checks
whether that browser can load the workstation-local Juice Shop image, and
enables its target link only after the tunnel responds. It cannot start or stop
containers and has no Docker socket, production credentials, or range-network
connection. Its Homepage health state represents only the safe launcher—not
the intentionally on-demand target or workstation tunnel.

Launch a disposable shell with basic HTTP tooling:

```bash
make purple-range-shell
```

Inside that shell, the authorized target is `http://juice-shop:3000`. Exit the
shell when the exercise ends. This initial toolbox deliberately contains only
`curl`; broader tooling belongs in the separately reviewed quiz attacker image.
That image bakes in `nmap`, `curl`, `dig`, and `nslookup`, runs as the upstream
unprivileged user with all Linux capabilities dropped, and is enabled only by
the generated range's explicit `attacker` profile. Use TCP-connect scans such
as `nmap -sT` because the toolbox is intentionally not granted raw sockets.

Prove isolation after the target is healthy:

```bash
make purple-range-verify
```

Reset or stop the range:

```bash
make purple-range-reset
make purple-range-down
```

Reset is destructive only to disposable range containers. No production
volume or network is in scope.

## Safety rules

- Use only targets explicitly listed in this document and attached exclusively
  to the range network.
- Never add host networking, privileged mode, the Docker socket, production
  secrets, production volumes, or a trusted-LAN network to a range service.
- Never bind a vulnerable target to `0.0.0.0` or a LAN address.
- Do not add outbound connectivity merely to install tools during an exercise;
  build and pin a reviewed attacker image beforehand.
- Stop and reset the range when an exercise ends.
- Treat any successful production or internet connectivity test as a safety
  failure, not an expected limitation.

## Next detection slice

After isolation passes on `brain`, add evidence collection in this order:

1. target application and container logs to the existing Loki pipeline;
2. exercise timestamps and a dedicated Grafana investigation view;
3. network evidence from a constrained Suricata sensor; and
4. selected Falco runtime events after its host privileges are explicitly
   reviewed.

Detection services must not create an escape path or copy attack payloads onto
Homepage. Homepage should link to a sanitized range status page only after live
verification.

## Vulnerability quiz rounds

Juice Shop remains the guided reference target. The planned quiz system uses
small reviewed applications with one seeded vulnerability class plus plausible
secure behavior and decoys. Its internal scenario manifest is versioned by
`schemas/vulnerability-quiz-scenario-v1.json` and generated by
`scripts/quiz_scenario.py`.

The generator selects a `/27` from `172.29.0.0/16`, removes every declared and
live Docker-network overlap, then assigns one target and three to eight decoys
to unique usable addresses. A seed makes a failed round reproducible without
exposing the answer key to the student-facing brief. Scenario creation fails
closed before printing a manifest when Docker cannot be reached, returns
partial or malformed inspection data, or reports an invalid subnet.

Generate a manifest while adding explicit non-Docker exclusions such as the
trusted LAN. Live Docker exclusions are always discovered and cannot be
disabled:

```bash
make quiz-scenario ARGS="--exclude 192.168.1.0/24 --exclude 172.24.0.0/16"
```

The internal manifest contains the answer key and must not be served through
Homepage, included in exercise logs, or committed as generated runtime state.

### Notification isolation acceptance

After deploying Alertmanager and ntfy, prove the range route is silent while
the ordinary production route remains deliverable:

```bash
make purple-range-alert-test
```

The bounded test submits two uniquely marked synthetic alerts directly to
Alertmanager. The Purple-Team alert carries `environment="purple_range"` and
`notification_policy="never"`; the production control does not. After the
immediate test route runs, the script uses ntfy's authenticated, read-only JSON
subscription API to require the production marker and reject the range marker.
It resolves both alerts on success, failure, or interruption. The phone should
receive only the production firing and recovery messages.

Live acceptance passed on 2026-08-06: Alertmanager discarded the marked
Purple-Team alert, the equivalent production control reached ntfy, and both
synthetic alerts were resolved after verification.

### First quiz template: expense IDOR

`docker/quiz-app/` contains the first reviewed template, **Acme Expense
Portal**. It authenticates two synthetic employees and exposes their synthetic
expense records through numeric API identifiers. In `vulnerable` mode, the
lookup verifies authentication but deliberately omits object ownership. In
`fixed` mode, the same lookup enforces ownership and returns the same `404`
shape for unauthorized and absent objects.

The pod has no published host port, outbound network requirement, persistent
volume, production data, file upload, or command-execution feature. Both modes
are tested through the real HTTP handler. The internal answer key lives in
`docker/quiz-app/templates/expense-idor.json`; future student briefs must not
expose that file or the scenario manifest's `target` object.

Validate the template without deploying a round:

```bash
make quiz-app-test
make quiz-app-config
```

### Notification boundary

Every quiz workload and derived alert must carry
`notification_policy="never"`. Alertmanager routes that label to an empty
`discard` receiver before any ntfy receiver. This silences expected vulnerable
findings, quiz deployment churn, resets, decoy availability, and exercise
traffic.

The policy does not suppress host-level alerts. CPU, memory, filesystem,
temperature, and controller availability alerts remain eligible for ntfy even
when resource pressure was caused by the range. Range services must not be
added to the production critical-service probe inventory.
