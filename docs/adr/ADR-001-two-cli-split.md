# ADR-001: Two-CLI Split — compliantflow is Read-Only

**Status:** Superseded
**Date:** 2026-01-01
**Deciders:** Engineering Lead

Superseded by adapter-mediated DHF automation facade: `CompliantFlowCore`
remains analysis-oriented, while the user-facing CompliantFlow CLI/SDK may
expose DHF automation operations through configured adapters/providers.

---

## Context

CompliantFlow needs to both read the DHF (for traceability, compliance checks, reporting) and write to it (creating items, transitioning lifecycle states). These two concerns could live in a single CLI or be split into two separate tools.

The DHF is also a regulated audit record — it must be trustworthy. A tool that can both evaluate the DHF and modify it introduces risk: a bug or misuse in the evaluation path could silently corrupt the very record it is checking.

## Decision

`compliantflow/` (the user-facing CLI package) is strictly read-only. All DHF mutations go through `python -m utils` in the `compliantflow-dhf` repository.

- `compliantflow`: analysis, traceability, compliance checking, reporting
- `python -m utils`: item CRUD, lifecycle transitions, schema validation

## Consequences

**Positive:**
- The compliance tool cannot corrupt the audit record it is evaluating
- Clear separation of concerns makes each tool independently testable
- `compliantflow` can be installed in any environment (including read-only CI) without write access to the DHF repo

**Negative:**
- Users must switch between two CLIs — operationally awkward for new users
- Two separate test suites and release cycles

**Constraints this imposes:**
- Never add `create`, `update`, `delete`, or `transition` commands to `compliantflow/`
- When AI agents need to mutate the DHF, they must invoke `python -m utils`, not `compliantflow`
