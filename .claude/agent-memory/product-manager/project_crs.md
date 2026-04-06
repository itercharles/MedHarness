---
name: Active Change Requests
description: Current CR status as of 2026-04-06 using the simplified two-state lifecycle (planned/completed)
type: project
---

## CR Lifecycle

CRs have two states: `planned` (identified, not yet merged) and `completed` (merged
to `main`). The PR merge is the approval event — no intermediate states exist.

## Completed CRs (CR-001 through CR-028)

All CRs from CR-001 to CR-028 are `completed` and merged to `main` as of 2026-04-06.

Notable completions this session:
- CR-026: Innolitics RDM migration tooling (`compliantflow migrate rdm`)
- CR-027: FDA 21 CFR Part 11 technical brief (`DHF/documents/technical_briefs/`)
- CR-028: GitLab CI and Jenkins artifact integration (`--provider` flag on `test pull`)

## Planned CRs (CR-029 through CR-034)

| CR ID | Title | Priority | Target |
|---|---|---|---|
| CR-029 | Multi-DHF / Multi-Project Support | High | v2.1.0 |
| CR-030 | Read-Only Compliance Status Web Dashboard | Medium | v2.1.0 |
| CR-031 | Ollama Air-Gap Deployment Package | Medium | v2.1.0 |
| CR-032 | PDF Submission Template Validation | Medium | v2.1.0 |
| CR-033 | (check DHF for details) | — | — |
| CR-034 | (check DHF for details) | — | — |

**How to apply:** v2.0.0 is complete. Next milestone is v2.1.0, starting with
CR-029 (Multi-DHF) as the highest-priority item.
