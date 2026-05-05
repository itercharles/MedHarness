# ADR-001: Single-Repo Tooling Model

**Status:** Accepted
**Date:** 2026-05-02

## Context

CompliantFlow previously operated as two repos (`CompliantFlow` + `CompliantFlow-DHF`).
`compliantflow init` cloned `CompliantFlow-DHF` at runtime. The separate repo
added complexity for contributors and made scaffolding depend on an external
Git remote.

## Decision

Merge `CompliantFlow-DHF` into `CompliantFlow`:
- `dhf_util/` bundled in the same wheel alongside `compliantflow/`
- `compliantflow init` scaffolds from bundled `dhf_util/templates/`
- No separate `dhf_util` pip package; install via `pip install compliantflow`

## Consequences

- Single checkout for contributors; both CLIs available after `pip install -e .`
- `init` has no network dependency; always uses bundled templates
- User DHF repos no longer contain `dhf_util/`, `pyproject.toml`, or engine source
- `pip install dhf_util` no longer works; install `compliantflow` instead
- `from dhf_util import ...` import paths unchanged
