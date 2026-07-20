# Engineering Standards

## Repository Standards

- Keep changes small, reviewable, and documented
- Prefer clear naming over abbreviations
- Avoid committing machine-specific transient artifacts
- Never commit real secrets

## Automation Contract

All automation entry points should be callable locally through `make` targets and scripts.

CI providers must call the same targets instead of duplicating shell logic:

- GitHub Actions: call `make <target>`
- GitLab CI: call `make <target>`
- Jenkins: call `make <target>`

## Documentation Standards

- Update docs in the same pull request as implementation
- Record assumptions and constraints explicitly
- Keep roadmap aligned with current repository state

## Quality Standards

- Add lint/test gates as tooling is introduced
- Keep scripts idempotent where practical
- Prefer explicit error messages and non-zero exits on failure

## Semantic Versioning

- Version independently deployable Homelab applications with `MAJOR.MINOR.PATCH`.
- Increment `PATCH` for compatible fixes, `MINOR` for compatible features, and
  `MAJOR` for incompatible application or API changes.
- Keep schema and event-contract versions independent from application versions;
  a compatible implementation release does not change a schema version.
- Update the application constant, local image tag, displayed version, and
  deployment documentation together where they apply.
- Current baselines are Dashboard `0.6.2`, Telemetry Collector `0.2.0`, Study
  Deck `0.2.0`, and dormant Security Status Adapter `0.1.0`.
- Display versions on Homepage only for Homelab-owned, independently released
  applications. Keep upstream service versions and image digests in Compose and
  operational documentation rather than repeating them across cards.

## Security Standards

- Use placeholder values for examples
- Keep secrets out of repository history
- Add security checks as first-class tasks in automation over time
