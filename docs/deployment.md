# Deployment Contract

## Scope

Homepage is the first service using the shared deployment contract. Local operators, GitHub Actions, and future CI systems call the same Make targets instead of embedding deployment logic in pipelines.

## Runtime layout on `brain`

The permanent Homepage deployment root is `/srv/homelab/homepage`:

```text
/srv/homelab/homepage/
├── current -> releases/<release-id>
├── previous -> releases/<release-id>
├── deployed.json
├── deployment.lock
└── releases/
    └── <version>-<commit>-<timestamp>/
        ├── compose.yaml
        ├── config/
        ├── glances.conf
        ├── release.json
        └── version.env
```

Releases are immutable snapshots. `current` is the active release and `previous` is the last-known-good rollback candidate. Each release records the dashboard semantic version, full Git commit, deployer, and UTC deployment timestamp. The top-level `deployed.json` describes the active release.

The deployment user must be able to manage Docker and write to `/srv/homelab/homepage`. One-time host preparation is intentionally separate from routine deployment:

```bash
sudo install -d -o dar -g dar /srv/homelab/homepage
```

If the self-hosted runner uses a different account, assign the directory to that account or a shared deployment group rather than running the workflow as root.

## Shared interfaces

| Target | Contract |
| --- | --- |
| `make homepage-validate` | Validate the Homepage configuration and resolved Compose model without changing runtime state |
| `make homepage-deploy` | Validate, stage an immutable release, activate it, and verify it |
| `make homepage-verify` | Verify the active Compose services and Homepage HTTP endpoint |
| `make homepage-rollback` | Activate and verify the last-known-good release |

The deployment root and verification endpoint may be overridden for controlled testing:

```bash
HOMEPAGE_DEPLOY_ROOT=/tmp/homepage-release HOMEPAGE_VERIFY_URL=http://127.0.0.1:3000 make homepage-deploy
```

## Safety behavior

- A non-blocking file lock rejects overlapping deployments and rollbacks.
- The stable Compose project name `homepage` prevents each release directory from creating a separate stack.
- Runtime images are pinned by digest; version comments in Compose identify the corresponding upstream release.
- Homepage accepts the LAN endpoint and `brain` hostname rather than wildcard host headers.
- Homepage reaches the Docker API through an internal read-only socket proxy. The proxy permits container queries and rejects POST operations; Homepage never mounts the Docker socket directly.
- A release is successful only when Homepage, Glances, and the Docker proxy are running, no service is unhealthy, and Homepage returns HTTP success.
- Failed verification automatically reactivates the prior managed release. If no prior managed release exists during the initial migration, the candidate is left running for inspection instead of tearing down the pre-existing Compose project.
- Rollback swaps `current` and `previous`, allowing an operator to recover from an accidental rollback.
- Generated Homepage logs and retired runtime files are excluded from release snapshots.

## Manual GitHub Actions release

Run the **Deploy Homepage** workflow from the GitHub Actions interface and select the Git revision to release. The workflow uses the self-hosted runner on `brain`, participates in a workflow-level production concurrency group, and calls the same Make targets used locally.

Production deployment remains manually triggered by policy. Pushes to `main` validate the repository but do not deploy automatically.

## Failure-path exercise

Use a disposable deployment root or a controlled maintenance window. Do not intentionally break the production endpoint without confirming console or SSH access.

1. Deploy a known-good revision with `make homepage-deploy`.
2. Deploy a second known-good revision to establish `previous`.
3. Set `HOMEPAGE_VERIFY_URL` to an unused local port and run `make homepage-deploy`; confirm the command fails and the earlier release remains active.
4. Run `make homepage-rollback`; confirm the last-known-good release becomes active and passes verification.
5. Inspect `current`, `previous`, `deployed.json`, and the active `release.json`.

## Troubleshooting

- **Lock already held:** wait for the active deployment to finish. Do not delete the lock file while a deployment process is running.
- **Permission denied under `/srv`:** correct ownership or deployment-group access; do not make the directory world-writable.
- **No rollback release:** complete two successful deployments before testing explicit rollback.
- **HTTP verification fails:** inspect `docker compose --project-name homepage --file /srv/homelab/homepage/current/compose.yaml ps` and container logs.
