# Post-Checklist

Verify each applicable item before opening a PR.

- [ ] **Schema valid** — `PYTHONPATH=.:DHF python -m utils validate schema` passes with no errors
- [ ] **Traceability clean** — `compliantflow --dhf DHF validate traceability` passes; no orphaned items
- [ ] **Coverage complete** — new items have both upstream and downstream links; chain UC→CRS→SYS→SRS→TC is unbroken
- [ ] **CR ID in PR title** — CI Phase 0 requires a CR ID in the PR title (e.g. `feat(CR-042): add input validation requirement`)
- [ ] **No stale cross-references** — if you updated an item title or ID, check that all `derives_from` / `links` fields referencing it are updated too
- [ ] **Test cases linked** — if the change affects SRS or SWDD items, confirm TC items have `@links` tags pointing to them
