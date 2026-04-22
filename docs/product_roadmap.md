# Product Roadmap

**Owner:** Product Manager
**Status:** Active
**Last reviewed:** 2026-04-22

CRs are the authoritative backlog — this document records milestone grouping, rationale, and exit criteria. Full CR descriptions live in `compliantflow-dhf/DHF/items/09_cr/`. Update this document when milestone scope or priority changes, not when individual CRs ship.

---

## Shipped — v2.0.x

| CR | Title |
|---|---|
| CR-041 | Draft Item Pre-Validation (`validate draft`) |
| CR-043 | Machine-Readable Compliance Report Export (`report compliance --format json`) |
| CR-054 | `compliantflow init` — interactive infrastructure onboarding |
| CR-055 | Product repo AI harness |
| CR-056 | AI-driven CR workflow (cr-analyze, cr-develop, cr-spec-iterate) |
| — | DHF repo AI harness (`AI-harness/` in dhf-template) |

---

## v2.1.0 — "Deepen & Enforce" (Q3 2026)

**Theme:** Strengthen the zero-debt guarantee and make compliance feedback actionable for engineers and AI agents.

| CR | Title | Priority |
|---|---|---|
| CR-035 | Actionable Compliance Feedback | High |
| CR-036 | ISO 14971 Policy Completeness | High |
| CR-037 | IEC 62304 Manual Check Reduction | High |
| CR-038 | Compliance Drift Detection | High |

**Exit criteria:**

- Compliance policy failures include actionable remediation steps (not just pass/fail)
- ISO 14971 check coverage is materially higher than v2.0.x baseline
- IEC 62304 manual check count reduced — more checks run automatically in CI
- Drift detection identifies compliance regressions across commits without full re-run

---

## v2.2.0 — "AI Coding Infrastructure" (Q4 2026)

**Theme:** Deepen the AI framework: machine-readable interfaces, richer agent context, broader standard coverage.

| CR | Title | Priority |
|---|---|---|
| CR-039 | Field Schema Protocol Extension *(unblocks CR-040)* | High |
| CR-040 | AI Agent Context Package | High |
| CR-042 | Compliance Status Summary Command | Medium |
| CR-044 | ISO 13485 Governance File | Medium |
| CR-045 | SOUP Automated Vulnerability Check | Medium |
| CR-046 | RDM Migration Completeness Validation | Medium |

**Exit criteria:**

- AI agents can query DHF schema and compliance state via structured APIs
- `compliantflow status` provides a single-command compliance posture summary
- ISO 13485 governance file delivered and integrated into compliance gate
- RDM migration path is validated end-to-end

---

## v3.0.0 — "Enterprise Motion" (H1 2027)

**Theme:** Sell to the QA Director, not just the engineering lead. Planned scope: RBAC, full Web UI, Jira/GitHub Issues sync, SOC 2 Type II, signed release artifacts + SBOM.

| CR | Title | Priority |
|---|---|---|
| CR-047 | 510(k) Submission Evidence Package *(requires active submission engagement)* | High |
| CR-048 | Compliance Posture REST API *(requires RBAC first)* | High |
| CR-049 | Compliance-Aware PR Review Agent | High |

**Exit criteria:**

- A customer can complete a 510(k) submission using CompliantFlow-generated evidence without manual assembly
- REST API exposes compliance posture with RBAC-enforced access
- Web UI is the primary interface for QA/RA engineers (CLI remains available)
- SOC 2 Type II audit completed

---

## Ongoing Cross-Cutting Work

These are continuous and should not be postponed:

- CI/CD reliability and evidence quality
- DHF traceability discipline (no orphaned items on main)
- AI harness accuracy — checklists and context.md kept current with architecture
- Test coverage for new compliance checks
- GETTING_STARTED.md accuracy for new users
