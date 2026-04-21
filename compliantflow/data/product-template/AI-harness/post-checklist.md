# Post-Checklist

Verify each applicable item before opening a PR.

- [ ] **Tests pass** — all existing and new tests pass locally
- [ ] **DHF updated if needed** — if the change adds/modifies behaviour, risks, or architecture, the corresponding DHF items are created or updated in the DHF repo
- [ ] **Traceability intact** — run `compliantflow --dhf ../$(basename {{dhf_repo}})/DHF validate traceability` and confirm no orphaned items
- [ ] **CR ID in PR title** — e.g. `feat(CR-042): add input validation` — CI Phase 0 requires this
- [ ] **No stale comments or TODOs** — no `# TODO`, `# FIXME`, or placeholder code left in
