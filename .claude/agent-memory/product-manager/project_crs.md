---
name: Active Change Requests
description: Current open CRs and their status/priority as of 2026-04-02
type: project
---

## Open / Active CRs

| CR ID | Title | Status | Priority | Target Version |
|---|---|---|---|---|
| CR-001 | Add bulk approval feature for requirements | `approved` | Medium | v2.1.0 |
| CR-007 | Defect: spec generation in SYSARCH page broken | `in_review` | High | v1.3.0 |

## Draft CRs (architectural / refactoring — deferred)

| CR ID | Title | Status | Notes |
|---|---|---|---|
| CR-004 | Improve format customization of frontend style | `draft` | Low priority / deferred |
| CR-005 | Improve effectiveness of auto testing | `draft` | Low priority / deferred |
| CR-014 | Move DHF data layer and test results into DHF/utils/ | `draft` | Architectural refactor |
| CR-015 | Fix adapter abstraction — remove loader/saver leakage | `draft` | Architectural refactor |
| CR-016 | Consolidate src/ layout | `draft` | Architectural refactor |
| CR-017 | Remove PR metadata from CR YAML — use GitOps-implicit linkage | `draft` | Architectural |
| CR-018 | Define component boundaries — DHF / compliantflow / tests | `draft` | Architectural |
| CR-019 | Test results — GitHub Actions artifacts as source of truth | `draft` | Architectural |
| CR-020 | Separate DHF utility docs and tests from product DHF | `draft` | Refactoring |
| CR-022 | Remove DHF-utils and interface items from product DHF (second pass) | `draft` | Refactoring |

## Recently completed / closed (v1.3.0)

- CR-003: PR gate + CR evidence report + traceability with test results — done (PRs #75–78)
- CR-006: ID auto-generation and immutability enforced — done (PR #81)
- CR-010: Centralize relationship configuration — `implemented`
- CR-011: Lifecycle status refactor — `cancelled` (superseded by current design, 2026-04-03)
- CR-012: CLI layer for CI/CD integration — `implementing` (substantially complete)
- CR-013: Split DHF data layer — `draft` (confirmed complete by user, may need status update)

## Roadmap CRs (v2.0.0 — defined 2026-04-02, not yet created in DHF)

| Proposed ID | Title | Priority | Target |
|---|---|---|---|
| CR-023 | ISO 14971 Governance Policy File | Critical | v2.0.0 |
| CR-024 | Release Gate Enforcement via CLI | High | v2.0.0 |
| CR-025 | Defect Lifecycle CI Hook | High | v2.0.0 |
| CR-026 | Innolitics RDM Migration Tooling | High | v2.0.0 |
| CR-027 | FDA 21 CFR Part 11 Technical Brief | High | v2.0.0 |
| CR-028 | GitLab CI and Jenkins Artifact Integration | High | v2.0.0 |

## Roadmap CRs (v2.1.0 — defined 2026-04-02, not yet created in DHF)

| Proposed ID | Title | Priority | Target |
|---|---|---|---|
| CR-029 | Multi-DHF / Multi-Project Support | High | v2.1.0 |
| CR-030 | Read-Only Compliance Status Web Dashboard | Medium | v2.1.0 |
| CR-031 | Ollama Air-Gap Deployment Package | Medium | v2.1.0 |
| CR-032 | PDF Submission Template Validation | Medium | v2.1.0 |

**Note:** CR-023 through CR-032 have been defined by the PM but NOT yet created as YAML files in DHF/items/09_cr/. Engineering team should review and create via `python -m utils item create --type CR`.

**How to apply:** All v1.3.0 commercial blockers are resolved. CR-007 (high-priority defect) and CR-001 (bulk approval, approved) are the near-term items. v2.0.0 planning should begin with CR-023 (ISO 14971) as the Critical-priority item.
