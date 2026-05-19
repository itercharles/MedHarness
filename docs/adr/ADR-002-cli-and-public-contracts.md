# ADR-002: CLI and Public Contracts

**Status:** Accepted
**Date:** 2026-05-02

## Context

After the single-repo migration, a need emerged to define which behaviors were
stable public contracts and which were internal implementation details.

## Decision

Establish explicit public contracts:
- Stable CLI commands for `medharness` (AI harness: `ci`, `cr`, `dhf context`)
- Stable CLI commands for `dhfkit` (data layer: `item`, `validate`, `doc`, `test`, `config`, `report`)
- Stable `dhfkit` import API
- Stable scaffold output structure and template variables
- Automation commands write JSON to stdout, interactive commands use stderr

Non-contracts (may change without MAJOR bump):
- Internal module layout
- Undocumented helpers
- Test utility code

## Consequences

- Contributors know what requires a design doc and MAJOR version bump
- CI verifies CLI command existence and output format
- `docs/compatibility-contracts.md` codifies the stable surface
- Sample item wording in templates is explicitly non-contract
