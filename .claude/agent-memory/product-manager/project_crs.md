---
name: Active Change Requests
description: CR status and roadmap as of 2026-04-07 — all CRs through CR-034 resolved; CR-035 to CR-049 are the active backlog
type: project
---

## CR Lifecycle

CRs have two states: `planned` (identified, not yet merged) and `completed` (merged
to `main`). The PR merge is the approval event — no intermediate states exist.
Closed/deferred CRs remain `planned` with rationale in `implementation_notes`.

## Completed CRs (all through CR-034)

All CRs from CR-001 to CR-034 are resolved as of 2026-04-07:

- **CR-001 to CR-029**: completed and merged to `main`
- **CR-030**: closed — CI already generates traceability + compliance PDFs as artifacts; web dashboard is redundant for QA/RA persona
- **CR-031**: deferred — OllamaBackend functional via env vars; no customer driving docker-compose packaging
- **CR-032**: deferred — submission format requirements are customer-specific; requires active submission engagement to scope
- **CR-033**: marked completed — field split (implementation_status / verification_status) was already implemented
- **CR-034**: marked completed — shared agent guidance consolidation was already implemented

**v2.0.0 is complete and ready for commercial release.**

## Active Backlog (CR-035 to CR-049)

Derived from `docs/product_strategy.md` three objectives. Full descriptions in `DHF/items/09_cr/`.

### v2.1.0 — "Deepen & Enforce" (Q3 2026)

| CR | Title | Priority |
|---|---|---|
| CR-035 | Actionable Compliance Feedback | High |
| CR-036 | ISO 14971 Policy Completeness | High |
| CR-037 | IEC 62304 Manual Check Reduction | High |
| CR-038 | Compliance Drift Detection | High |

### v2.2.0 — "AI Coding Infrastructure" (Q4 2026)

| CR | Title | Priority |
|---|---|---|
| CR-039 | Field Schema Protocol Extension *(prerequisite for CR-040, CR-041)* | High |
| CR-040 | AI Agent Context Package | High |
| CR-041 | Draft Item Pre-Validation | High |
| CR-042 | Compliance Status Summary Command | Medium |
| CR-043 | Machine-Readable Compliance Report Export | High |
| CR-044 | ISO 13485 Governance File | Medium |
| CR-045 | SOUP Automated Vulnerability Check | Medium |
| CR-046 | RDM Migration Completeness Validation | Medium |

### v3.0.0 — "Enterprise Motion" (H1 2027)

Existing planned scope: RBAC, full Web UI, Jira/GitHub Issues sync, SOC 2, signed artifacts + SBOM. New additions:

| CR | Title | Priority |
|---|---|---|
| CR-047 | 510(k) Submission Evidence Package *(needs active submission engagement)* | High |
| CR-048 | Compliance Posture REST API *(needs RBAC first)* | High |
| CR-049 | Compliance-Aware PR Review Agent | High |
