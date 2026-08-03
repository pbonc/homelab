# Isolated Purple-Team Range

## Purpose and authorization

The range exists for defensive learning against deliberately vulnerable,
lab-owned targets. Authorization covers only containers attached to the
`homelab-purple-range-target` network. It does not cover `brain`, `piaware`,
other trusted-LAN devices, public systems, or third-party services.

The first target is OWASP Juice Shop 20.0.0, an intentionally insecure training
application. Its image is pinned to the verified Linux AMD64 manifest digest.
The target is never published to all host interfaces: Docker binds it only to
`127.0.0.1:3008` on the range host.

## Threat model

The primary hazard is that a deliberately vulnerable target or attacker tool
could reach production services, the trusted LAN, or the internet. Secondary
hazards are persistent compromised state, accidental long-running exposure,
resource exhaustion, and reuse of production credentials.

The first slice applies these controls:

- a dedicated Docker network with `internal: true`;
- a loopback-only target port rather than a LAN listener;
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

Launch a disposable shell with basic HTTP tooling:

```bash
make purple-range-shell
```

Inside that shell, the authorized target is `http://juice-shop:3000`. Exit the
shell when the exercise ends. This initial toolbox deliberately contains only
`curl`; broader tooling belongs in a separately reviewed attacker image.

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
