# Homelab Push Notifications

## Delivery boundary

The first notification client is an iPhone, and the ntfy server is intentionally
reachable only from the trusted home LAN. No router port forwarding, public
reverse proxy, or anonymous internet access is part of this design.

The iPhone ntfy app must use the exact LAN base URL configured by the server.
While the phone is away from the home network, it cannot retrieve notification
content. Returning to the LAN restores access. Remote delivery can be revisited
later through an authenticated private VPN, but it is not required for the
initial release.

## iPhone wake-up path

iOS does not allow a self-hosted application to maintain unrestricted
background connections. For timely notifications, the self-hosted server will
set:

```yaml
upstream-base-url: https://ntfy.sh
```

For each local publication, the upstream service receives only a generic poll
request containing the message ID and a hash derived from the topic URL. The
notification title, body, Homelab state, and credentials remain on the local
server. After Apple wakes the ntfy app, the app connects back to the LAN server
to retrieve the real message.

If the phone cannot reach the LAN server, iOS may show only a generic
notification or delay retrieval until the phone returns home. This is accepted
behavior for the LAN-only release and must not trigger router exposure as a
troubleshooting shortcut.

## Security model

- ntfy listens only on Brain's trusted-LAN address.
- Authentication is enabled with default access set to `deny-all`.
- Public signup and anonymous publishing are disabled.
- Alertmanager receives a write-only publisher credential.
- The phone receives a separate read-only subscriber credential.
- Credentials, access tokens, auth databases, and optional Web Push keys remain
  in ignored runtime storage.
- Topic names are descriptive identifiers, not secrets or access controls.
- Notification content contains concise operational summaries and safe links,
  never credentials, private Aikido finding details, aircraft identities, or
  sensitive infrastructure metadata.

## Initial event policy

The first delivery path is Prometheus Alertmanager to ntfy. Prometheus remains
the source of alert truth; ntfy is only a delivery channel. Initial phone
notifications are limited to:

- sustained service outages;
- critical disk pressure and other actionable resource exhaustion;
- stale telemetry or receiver data after its established threshold;
- failed deployments and backups; and
- meaningful security-state changes that can be represented without finding
  details.

Resolved notifications are sent so the phone shows recovery. Routine successes,
short transient failures, and informational state changes stay out of the phone
channel. Alertmanager grouping, inhibition, and repeat intervals prevent one
incident from producing a stream of duplicate messages.

## Expanded event policy

Hardware-node loss is actionable only after ten continuous minutes. Prometheus
applies that threshold to the Brain and PiAware Node Exporter targets and sends
a recovery when the target returns. A complete Brain outage is a special blind
spot: Brain currently hosts Prometheus, Alertmanager, and ntfy, so it cannot
deliver its own outage notification. Closing that gap requires a small
independent observer on PiAware or another always-on node; pretending the
controller can self-page while powered off would provide false confidence.

New-device detection will use a local inventory watcher rather than raw
one-off ARP events. A device must be observed repeatedly before it is considered
new, and notifications will include only a locally assigned name when known,
address, MAC address, and offline vendor label. Randomized client MAC addresses
and brief Wi-Fi roaming must not create notification storms. Device departures
remain dashboard-only by default; known infrastructure disappearing is handled
by the sustained hardware alerts.

The recommended next low-noise notifications are:

- sustained high CPU temperature or thermal throttling;
- critical filesystem pressure and storage-device health changes;
- stale or failed encrypted backups;
- stale weather and ADS-B ingestion after their established grace periods;
- failed deployments with a recovery or subsequent successful deployment;
- meaningful Aikido severity changes without vulnerability details; and
- future certificate-expiration warnings once internal TLS exists.

Routine package updates, successful scheduled jobs, normal device departures,
individual aircraft, and short resource spikes do not belong in the immediate
phone channel. They can become a daily digest later if a digest proves useful.

## First deployment

On `brain`, create two ignored credentials and validate the Compose model:

```bash
cd ~/git/homelab
make ntfy-secrets
make ntfy-config
make ntfy-up
docker compose --env-file docker/ntfy/.env \
  --file docker/ntfy/compose.yaml ps
curl --fail --silent --show-error \
  http://192.168.1.23:8093/v1/health
```

The setup creates `homelab-publisher` with write-only access and
`homelab-iphone` with read-only access to `homelab-alerts`. Their passwords are
stored in ignored files under `docker/ntfy/secrets/`; only bcrypt hashes are
passed to the server. Run `make ntfy-secrets` once. Credential rotation is
deliberate: stop ntfy, remove its generated `.env` and password files, rerun the
target, then restart the service.

In the iPhone ntfy app, add `http://192.168.1.23:8093` as a server, authenticate
as `homelab-iphone`, and subscribe to `homelab-alerts`. The subscriber password
can be displayed locally on Brain when entering it into the phone:

```bash
cat docker/ntfy/secrets/subscriber_password.txt
```

After the subscription exists, send one authenticated message:

```bash
make ntfy-test-publish
```

Do not paste either password into chat, Git, shell history, documentation, or
the Homepage configuration.

## Alertmanager delivery policy

Prometheus sends firing and resolved alerts to the digest-pinned Alertmanager
service. Alertmanager groups by alert name, service, and instance, waits 30
seconds for related signals, delays changes to an existing group for five
minutes, and repeats a continuously firing incident at most every four hours.
The critical root-disk alert inhibits the corresponding lower-threshold warning.

Alertmanager reads the write-only ntfy publisher password from
`docker/ntfy/secrets/publisher_password.txt` through a read-only container
mount. Its ignored parent directory is mode `0700`; the mounted publisher file
is mode `0644` so the non-root Alertmanager process can read it. The separate
iPhone password and generated environment remain mode `0600`. The password is
never embedded in Alertmanager configuration. Notifications use ntfy's built-in
Alertmanager template, contain at most ten alerts per delivery, and include
resolved messages.

After deploying the observability stack, exercise the complete delivery path
without stopping a real service:

```bash
make observability-config
make observability-up
make alertmanager-test
```

The test creates a clearly labeled synthetic alert, waits for its firing
notification, and then resolves it. The recovery notification can arrive about
ten seconds after the command finishes. Confirm both messages on the iPhone.

## Acceptance boundary

The first release is accepted only when:

1. an authenticated test notification arrives while the iPhone is on the home
   Wi-Fi;
2. an Alertmanager firing notification and its resolved notification arrive as
   a grouped pair;
3. anonymous publish and subscribe attempts are denied;
4. invalid credentials fail without exposing tokens in logs;
5. an ntfy outage does not erase the underlying Prometheus alert state;
6. the phone-off-LAN limitation is observed and documented rather than bypassed;
   and
7. restarting ntfy preserves the intended bounded cache and access-control
   state.
