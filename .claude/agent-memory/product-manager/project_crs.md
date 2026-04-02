---
name: Active Change Requests
description: Current open CRs and their status/priority as of 2026-04-02
type: project
---

| CR ID | Title | Status | Priority | Target Version |
|---|---|---|---|---|
| CR-001 | Add bulk approval feature for requirements | approved | Medium | 1.3.0 |
| CR-003 | Automated PR-CR Linking and Traceability System | approved | High | 1.1.0 |
| CR-004 | Improve format customization of frontend style | draft | — | — |
| CR-005 | Improve effectiveness of auto testing | draft | — | — |
| CR-006 | Object IDs shall be generated automatically and not editable | in_review | High | — |

**Why these matter:**
- CR-003 (highest priority approved CR) targets automated PR↔CR linking via GitHub Actions — this is a regulatory gap (IEC 62304 §6.2 change control). It has the most extensive affected_items list (~100 items).
- CR-006 addresses a real UX/data-integrity risk: if IDs are manually editable, references can break silently.
- CR-001 targets QA team efficiency — bulk approval is a common request for large batches.
- CR-004 and CR-005 are draft with no full specification — likely low-priority or backlog items.

**How to apply:** When prioritizing near-term work, CR-003 and CR-006 should be treated as committed items for the next release cycle. CR-001 is already approved for v1.3.0.
