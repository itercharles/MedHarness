# Changelog

All notable changes to MedHarness are documented in this file.

MedHarness follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to CLI, templates, scaffold output, or public API
- **MINOR** — backward-compatible new features
- **PATCH** — bug fixes, doc corrections, non-behavioral internal changes

---

## [0.3.3] — 2026-05-09

### Features

- `ci artifacts generate` now emits a PDF traceability matrix
  (`Requirements_Traceability_Report.pdf`) alongside the existing JSON report
  when WeasyPrint is installed (`pip install medharness[docs]`). The PDF
  renders the full UC → CRS → SYS → SRS → SWDD chain with per-level coverage
  statistics, per-item verification status, and a JUnit-derived test result
  summary. JSON output is unchanged so compliance gates continue to work.

### Fixes

- `_write_traceability_report` previously discarded the caller-supplied
  `.pdf` extension and wrote JSON only. The path is now honored: a `.pdf`
  output produces a PDF (with JSON written next to it as `.json`).

---

## [0.3.2] — 2026-05-08

### Features

- `ci design-cr` now runs a second LLM pass after DHF item generation to review the output
  against the approved spec. The review is written to
  `docs/cr-specs/<CR_ID>-Design-Review.md` and committed alongside the design artifacts.
- `ci develop-cr` now runs a second LLM pass after code generation to review the
  implementation against the approved spec. The review is written to
  `docs/cr-specs/<CR_ID>-Code-Review.md` and committed with the implementation.
- Both reviews check completeness, traceability, test annotations, and coding conventions.
  They are non-blocking — the stage advances regardless of the verdict.

---

## [0.3.1] — 2026-05-07

### Changes

- `cr_analyze.md`: removed redundant step; analyze phase now identifies DHF items that will
  need creation but does not create them (creation is design phase only)
- `req_manage.md`: removed "do not edit" restriction (skill is also used in design phase);
  added explicit "no change > update > create" preference
- All impact skills (`product_impact.md`, `architecture_impact.md`, `risk_impact.md`,
  `soup_impact.md`, `test_impact.md`): added "no change > update > create" preference
  to Design Updates sections
- Removed `AI-harness` template directory and `.claude/skills` scaffolding from `medharness init`

---

## [0.3.0] — 2026-05-06

### Features

- CI CR lifecycle commands: `ci analyze-cr`, `ci design-cr`, `ci develop-cr` for LLM-driven
  spec generation, DHF design, and code implementation
- Single-repo CR lifecycle: analyze → design → code phases driven by GitHub Actions
- `ci validate-spec` validates spec YAML front-matter (cr_id, direction_fit, affected_items,
  test_plan) with self-correction loop on failure
- `ci dhf-validate` structural gate: schema + traceability checks for CI pipelines
- `ci test-coverage` requirement-to-test coverage gate using JUnit XML evidence
- `ci evidence bundle` and `ci evidence import` for DHF artifact bundling

---

## [0.2.1] — 2026-05-06

### Fixes

- `medharness cr workflow intake-github-issue-ci --open-pr` now passes `--repo`
  explicitly to `gh` PR commands and fails with the actual CLI error when PR
  lookup or creation fails, instead of silently returning an empty `pr_url`

---

## [0.2.0] — 2026-05-05

### Breaking Changes

- `medharness init` now scaffolds into the **current directory** (single-repo layout); the
  separate DHF repo is gone — DHF lives at `DHF/` alongside product source code
- `medharness init` is now **zero-prompt** — no questions about org, repo name, or project name;
  everything is derived from the current directory name
- `_replace_placeholders` no longer accepts a `product_repo` argument
- Generated `cr-complete.yml` uses `GITHUB_TOKEN` only — `DHF_REPO_TOKEN` is no longer required

### Features

- `engineering-control.yml` now has four explicit CI phases: CR validation, DHF schema +
  traceability validation, test coverage gate, evidence bundle (post-merge)
- Test step is language-agnostic with commented examples for pytest, Jest, Maven, and Go;
  only contract is JUnit XML output to `test-results/`
- `.gitignore` is scaffolded automatically

### Changes

- `cr-analyze.yml` and `cr-develop.yml` updated for single-repo: use `github.repository`
  and `GITHUB_TOKEN` instead of cross-repo `PRODUCT_REPO_TOKEN`
- DHF README placed at `DHF/README.md` instead of the repo root
- `AI-harness/context.md` removed from scaffold — `CLAUDE.md` covers the same purpose

### Fixes

- `engineering-control.yml` install step now uses `pip install medharness` (was broken
  `gh release download` with unfilled `{github_org}/{dhf_repo_name}` placeholders)

---

## [0.1.0] — 2026-05-03

### Breaking Changes

- Merged `MedHarness-DHF` into `MedHarness` — single-repo tooling model
- `medharness init` no longer fetches from a remote repo; scaffolds from bundled templates
- `dhfkit` is no longer a separate `pip install dhfkit` package; included in `medharness`
- `medharness init` no longer accepts `--template-ref` (templates are bundled)
- Removed `pip install -e dhf/` dependency from generated CI workflows
- Generated DHF repos no longer contain `dhfkit/`, `pyproject.toml`, or `.github/prompts/`

### Features

- All DHF operations unified under `medharness dhf` (item, validate, doc, test, config, context)
- `dhfkit/templates/` — starter DHF scaffold with 12 sample items
- `docs/architecture.md` — stable architecture documentation
- `docs/adr/` — architecture decision records for major design choices
- Scaffold generates item subdirectories from doc type configs

### Fixes

- Template docs (j2) updated to reflect single-repo model
- Scaffolded GitHub Actions workflows updated for new install flow
- Example project items reflect current architecture
- Removed stale `MedHarness-DHF` references from code, docs, and fixtures

### Migration Notes

See [docs/adr/ADR-001-single-repo-tooling-model.md](docs/adr/ADR-001-single-repo-tooling-model.md) for the migration rationale.

---

## Version History Legend

- **Breaking Changes** — incompatible changes requiring user action
- **Features** — new backward-compatible capabilities
- **Fixes** — bug fixes and corrections
- **Migration Notes** — steps required to upgrade

---

*Changelog format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).*
