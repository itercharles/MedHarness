# AGENTS.md

CompliantFlow is a compliance checking tool for medical device software. It connects to
a project's Design History File (DHF) through a defined interface (CLI or API) and
verifies compliance against IEC 62304, ISO 14971, and IEC 82304-1 in CI. The interface
abstraction means it can integrate with any DHF system, not just the reference
implementation in this repo.

This repository uses CompliantFlow on itself: `DHF/` is CompliantFlow's own design
history file, serving as both the tool's regulatory documentation and a working example
of how it operates.

## Environment

```bash
.venv/            # virtual environment
PYTHONPATH=.:DHF  # required for all commands
```

## Key Invariants

**Two-CLI split.** `CompliantFlowCore` (`compliantflow/`) is read-only — analysis,
traceability, compliance, reporting. DHF mutations (create, update, delete, lifecycle
transitions) go through `python -m utils`. Do not add write operations to
`CompliantFlowCore`.

**Graph edge direction.** Edges in `compliantflow/graph.py` run child → parent.
`descendants()` means business-upstream (toward requirements). `ancestors()` means
business-downstream (toward tests). This is the opposite of the natural reading.

**GitOps approval.** Requirement item types (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`,
`SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit
status field change needed. Feature branches mean draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions
via `python -m utils item transition`. These are not GitOps-approved.

---

## CR Workflow

CR items use two statuses: `planned` (not yet implemented) and `closed` (merged to `main`).

- Confirm the CR is `planned` before writing any code. Create it with `python -m utils item create --type CR` if it does not exist.
- If the CR involves new tests, read `tests/fixtures/test_data.py` and the relevant doc type configs first — field mismatches are the most common source of iteration.
- Set the CR to `closed` in the same commit as the implementation.
- If opening a PR, include the CR ID in the title — CI Phase 0 requires it.

Do not run compliance checks as a default validation step — they invoke an LLM and are only needed when changing compliance engine or governance files.

