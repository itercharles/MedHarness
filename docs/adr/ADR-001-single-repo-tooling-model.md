# ADR-001: Single-Repo Tooling Model

**Status:** Accepted
**Date:** 2026-05-02

## Context

MedHarness previously operated as two repos (`CompliantFlow` + `CompliantFlow-DHF`).
`medharness init` previously cloned `CompliantFlow-DHF` at runtime. The separate repo
added complexity for contributors and made scaffolding depend on an external
Git remote.

## Decision

Merge the former DHF companion repo into the main MedHarness repository:
- `dhfkit/` is bundled in the same wheel alongside `medharness/`
- `medharness init` scaffolds from bundled `dhfkit/templates/`
- the DHF engine ships with `pip install medharness`

## Consequences

- Single checkout for contributors; both CLIs available after `pip install -e .`
- `init` has no network dependency; always uses bundled templates
- User DHF repos no longer contain `dhfkit/`, `pyproject.toml`, or engine source
- the DHF engine is installed through `medharness`
- `from dhfkit import ...` import paths remain stable
