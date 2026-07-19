# Security

## Aikido scope

> Operational status (2026-07-19): Aikido's Public REST API returns HTTP 402
> for this workspace. Live polling is disabled, producing zero adapter API
> calls. Homepage retains a static dashboard link, and repository scanning
> through the read-only GitHub App remains active. Adapter source and tests are
> retained for a possible future entitlement.

Aikido is connected to the `pbonc/homelab` repository through its read-only
GitHub App integration. Additional repositories may be connected later. Autofix
and other write-capable integrations remain disabled.

## Initial baseline

The first Aikido scan completed with three open findings. This count records the
starting point; it is not an acceptance of the findings or a permanent expected
count. Finding details are intentionally not duplicated in the repository.

Baseline remediation was explicitly deferred for later security work. No
finding is accepted solely because it existed in the initial scan: deferred
findings remain actionable in Aikido until individually reviewed. Any future
risk acceptance must record the reason, owner, review date, and expiration or
reconsideration trigger. Critical and high-severity gating will be enabled only
after that baseline triage, without granting automatic-fix write access.

## Homepage status boundary

Homepage must never receive Aikido client credentials, access tokens, or finding
details. The dormant server-side adapter can publish a LAN-only summary containing:

- Counts for open critical, high, medium, and low findings
- The state derived from the highest actionable severity
- The time of the last successful refresh
- Whether the cached result is stale
- A link to the Aikido dashboard

When enabled, the adapter uses OAuth 2.0 Client Credentials. Its client ID and client
secret will live in ignored runtime secret files on `brain`, not in environment
examples, browser code, logs, or repository history.

Polling remains disabled while API access is plan-restricted.

## Adapter operations

The dormant adapter source and Compose stack live in `docker/security-status/`.
When enabled, it listens on LAN port `8010`, polls every 15 minutes, and
considers cached data stale after one hour. It is not in the active runtime
inventory; the following operations are retained for reversibility.

The HTTP surface is a minimal ASGI application served by Uvicorn. It deliberately
does not depend on FastAPI or Starlette; two JSON endpoints do not justify the
additional framework dependency or vulnerability surface.

On `brain`, create the ignored runtime files interactively and start the stack:

```bash
make security-secrets
make security-config
docker compose --env-file docker/security-status/.env --file docker/security-status/compose.yaml up --detach --build
```

`make security-secrets` does not echo credentials and does not overwrite
existing values. Its secrets directory is host-private (`0700`); individual
files are `0644` because Compose file-backed secrets retain host permissions
and the container runs as a non-root user. Verify the sanitized endpoint without
displaying credentials:

```bash
curl --fail --silent --show-error http://127.0.0.1:8010/api/status
```

The response may include repository name, aggregate counts, state, freshness,
and the Aikido dashboard URL. It must not include API credentials, access
tokens, finding names, file paths, or vulnerability details.

## Status semantics

- `clear`: no actionable open findings
- `low_medium`: one or more low or medium findings, with no high or critical finding
- `high`: one or more high findings, with no critical finding
- `critical`: one or more critical findings
- `stale`: the last successful result is older than the configured freshness limit
- `unavailable`: no successful result is available

The adapter counts individual open issues across the workspace rather than
grouped feed records. This includes repository, surface-monitoring, SCM,
container, and other findings, and automatically covers repositories connected
later. Accepted, ignored, snoozed, and closed findings do not determine the
Homepage card color. Baseline findings remain actionable until they are
individually triaged.
