# ADR-003: Templates as Starter DHF

**Status:** Accepted
**Date:** 2026-05-02

## Context

The repo had two maintained DHF sources: `dhfkit/templates/` (scaffold
source) and `examples/reference-dhf-project/` (runnable example). Duplicated
config, spec templates, and plans caused maintenance drift.

## Decision

Fold the example into templates, making `dhfkit/templates/` the sole
scaffold source:
- Add 12 sample items (one per doc type) directly in templates
- Delete `examples/reference-dhf-project/`
- Tests scaffold a temp DHF from templates at runtime

## Consequences

- Single source of truth for scaffold content; no duplicated trees
- `medharness init` produces a starter DHF with sample items
- CLI output warns users to replace sample content
- Template README and development plan include "replace me" guidance
- Test fixtures use `_scaffold_dhf()` instead of a static example project
