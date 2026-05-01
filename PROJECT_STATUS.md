# Project Status

> **Last updated:** 2026-05-01
>
> This file summarizes the current harness surface in `CompliantFlow`.
> Formal product documents remain canonical in the DHF repo created from `CompliantFlow-DHF`.

---

## Stable Now

- `compliantflow init` for product-side scaffolding and DHF template fetch
- `ci test-coverage` for requirement-to-test coverage checks from JUnit evidence
- `ci evidence bundle` for runtime evidence bundle generation
- `ci release consume-artifact` and `ci release assemble` for release pipeline support
- `cr workflow` for CR-linked automation

## Evolving

- agent context and repo-guidance generation
- migration tooling
- command output formats for status-style reporting

## Out of Scope for This Repo

- canonical product strategy, architecture, and process documents
- DHF item ownership and document template authority
- product-specific code, tests, and release logic

Those responsibilities live in the DHF repo and product repo, not in this
harness repository.
