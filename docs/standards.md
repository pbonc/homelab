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

## Security Standards

- Use placeholder values for examples
- Keep secrets out of repository history
- Add security checks as first-class tasks in automation over time
