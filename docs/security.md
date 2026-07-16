# Security

## Aikido scope

Aikido is connected to the `pbonc/homelab` repository through its read-only
GitHub App integration. Other repositories are outside this project's scanning
scope. Autofix and other write-capable integrations remain disabled.

## Initial baseline

The first Aikido scan completed with three open findings. This count records the
starting point; it is not an acceptance of the findings or a permanent expected
count. Finding details are intentionally not duplicated in the repository.

Baseline triage is deferred. Until each finding is reviewed, no finding should
be marked accepted solely because it existed in the initial scan, and security
gating must remain disabled.

## Homepage status boundary

Homepage must never receive Aikido client credentials, access tokens, or finding
details. A server-side adapter on `brain` will obtain short-lived access tokens,
query only the `homelab` repository, and publish a LAN-only summary containing:

- Counts for open critical, high, medium, and low findings
- The state derived from the highest actionable severity
- The time of the last successful refresh
- Whether the cached result is stale
- A link to the Aikido dashboard

The adapter will use OAuth 2.0 Client Credentials. Its client ID and client
secret will live in ignored runtime secret files on `brain`, not in environment
examples, browser code, logs, or repository history.

Polling is preferred over inbound webhooks because `brain` is not exposed to the
public internet. The initial polling interval will be conservative and cached
results will be served when Aikido is temporarily unavailable.

## Status semantics

- `clear`: no actionable open findings
- `low_medium`: one or more low or medium findings, with no high or critical finding
- `high`: one or more high findings, with no critical finding
- `critical`: one or more critical findings
- `stale`: the last successful result is older than the configured freshness limit
- `unavailable`: no successful result is available

Accepted, ignored, snoozed, and closed findings do not determine the Homepage
card color. Baseline findings remain actionable until they are individually
triaged.
