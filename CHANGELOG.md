# Changelog

All notable changes to MedHarness are documented in this file.

MedHarness follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to CLI, templates, scaffold output, or public API
- **MINOR** — backward-compatible new features
- **PATCH** — bug fixes, doc corrections, non-behavioral internal changes

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
