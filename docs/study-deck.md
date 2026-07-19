# Homelab Study Deck

## Purpose

The Study Deck turns deployed homelab decisions, failures, and recovery
exercises into short review sessions and interview talking points. It is a
LAN-only learning aid, not a source of operational truth. Every answer and note
must cite a version-controlled document under `docs/`.

## Content and progress boundary

Question and note content lives in `docker/study-deck/content/deck.json` and
uses `schemas/study-deck-v1.schema.json`. Content is reviewed and committed like
code. The initial deck covers deployment rollback, runtime status semantics,
telemetry architecture, security boundaries, Prometheus retention, hardware
capacity, and deployment events.

Personal progress lives in SQLite at `/data/study.db` inside the persistent
`study-deck-data` volume. It is never committed. Container recreation preserves
progress; deleting the named volume permanently resets it.

## Review behavior

Daily review selects due or unseen questions. Interview mode limits the session
to questions that exercise architecture, tradeoffs, failure handling, and
security explanations. Choices are shuffled for every session. After answering,
the service reveals the correct choice, explanation, and repository source.

Correct answers with confidence three or higher advance through intervals of
one, three, seven, fourteen, and thirty days. Low-confidence correct answers
remain in the current box; incorrect answers return to a ten-minute interval.

## Operations

```bash
make study-test
make study-config
make study-up
curl --fail --silent --show-error http://192.168.1.23:8020/api/health
```

Open `http://192.168.1.23:8020`. Stop the container without deleting progress
with `make study-down`.

Export a versioned progress backup without copying the live SQLite database:

```bash
curl --fail --silent --show-error \
  http://192.168.1.23:8020/api/progress/export \
  --output study-progress.json
```

Restore it with:

```bash
curl --fail --silent --show-error \
  --header "Content-Type: application/json" \
  --data-binary @study-progress.json \
  http://192.168.1.23:8020/api/progress/restore
```

Restore validates the schema and question IDs, then replaces existing personal
progress. Backups contain question IDs and review history, never answer text or
credentials. `DELETE /api/progress` remains the deliberate reset operation.

The service is bound to the trusted LAN address, drops all Linux capabilities,
prevents privilege escalation, and uses a read-only root filesystem. The SQLite
volume is its only persistent writable path. Question content must never include
credentials, private Aikido finding details, or actionable purple-team payloads.
