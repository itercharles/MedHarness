# Architecture

CompliantFlow is the product-facing harness in a two-repo design-control model.
This document describes the harness boundary. Canonical architecture for the
product family lives in the DHF repo under
`DHF/documents/specs/architecture_design_specification.md`.

---

## Boundary

| Repo | Primary responsibility |
|------|------------------------|
| `CompliantFlow` | scaffolding, CI gates, evidence-bundle orchestration, agent entrypoints |
| `CompliantFlow-DHF` | DHF structure, document templates, `dhf_util`, traceability rules |
| Product repo | implementation code and executable tests |
| DHF repo | controlled requirements, design, risk, and change records |

The harness reads DHF structure and test evidence. It does not own the formal
DHF documents or item schemas.

---

## Runtime Interaction

1. `compliantflow init` fetches the DHF template from `CompliantFlow-DHF`.
2. Product repos receive scaffolded CI workflows and a minimal `CLAUDE.md`.
3. Product CI runs tests, emits JUnit XML, and invokes `ci test-coverage`.
4. On merge to `main`, product CI generates an evidence bundle from runtime artifacts.

---

## Agent Guidance

Agent guidance is document-grounded. This repo provides local harness guidance,
while formal product direction and process rules are read from the DHF-side
canonical documents:

- `DHF/documents/specs/customer_requirement_specification.md`
- `DHF/documents/specs/architecture_design_specification.md`
- `DHF/documents/plans/development_plan.md`
