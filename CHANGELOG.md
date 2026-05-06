# Changelog

All notable changes to MedHarness are documented in this file.

MedHarness follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to CLI, templates, scaffold output, or public API
- **MINOR** — backward-compatible new features
- **PATCH** — bug fixes, doc corrections, non-behavioral internal changes

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
