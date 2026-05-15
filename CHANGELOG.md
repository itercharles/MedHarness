# Changelog

All notable changes to MedHarness are documented in this file.

MedHarness follows [Semantic Versioning](https://semver.org/):
- **MAJOR** — breaking changes to CLI, templates, scaffold output, or public API
- **MINOR** — backward-compatible new features
- **PATCH** — bug fixes, doc corrections, non-behavioral internal changes

---

## [Unreleased]

### Breaking Changes

- **`workflow_intake_github_issue` and `workflow_intake_github_issue_ci` no longer return deprecated spec fields**
  - The keys `spec_generated`, `spec_status`, `spec_validation`, `spec_path`,
    `spec_json_path`, and `spec_error` have been removed from both functions'
    return dicts. They were previously stubbed to `false`/`null` since the
    spec-generation phase was removed in 0.5.0. Callers that unpack these
    keys from the Python API or parse them from CLI JSON output must remove
    those references.

### Changes

- Removed unused `_get_document_with_legacy_fallback` helper from `_helpers.py`
  (legacy `docs/cr-specs/` fallback path, no callers).
- `ci generate-dhf` and `ci develop-cr` now emit per-error `field`/`issue`/`Fix:`
  detail lines to stderr when validation errors remain after generation, matching
  the existing pattern in `ci validate-code` and `ci validate-branch`.
- `cr_review_code.md` prompt updated: references CR item via
  `medharness --dhf DHF dhf item show {{cr_id}}` instead of the removed
  `docs/cr-specs/` file path; review output written to `docs/reviews/`.
- Added golden E2E integration tests (`test_generate_dhf_e2e.py`) covering
  `generate_dhf` and `generate_code` orchestration with a stubbed Claude CLI.

---

## [0.5.0] — 2026-05-14

### Changes

- **Remove cr-spec phase; collapse design+dev into single generate-dhf → develop-cr flow**
  - `ci analyze-cr` and `ci design-cr` commands removed. The new two-phase flow is
    `generate-dhf` (design + DHF items + implementation plan) followed by `develop-cr` (code).
  - `generate-dhf` now includes triage (duplicate / out-of-scope / too-large /
    architecture-conflict), V-model DHF cascade, and writes a structured
    implementation plan into `implementation_notes` on the CR item.
  - `generate-dhf` reads relevant source modules before writing SWDD items so
    the reviewed design reflects the actual codebase. SWDD is only created when
    a genuine design decision exists (threshold rule baked into prompt).
  - `develop-cr` reads `implementation_notes` as its primary implementation spec;
    runs `medharness ci test-coverage` after tests to verify requirement coverage;
    reconciles `implementation_notes` and SWDD items if implementation deviated.
  - CR lifecycle simplified: `new → design → develop → completed` or `new/design → rejected`.
    State transitions are recorded for traceability but not enforced as CI gates.
  - `validate-spec` and `validate-design` commands removed; `validate-code` and
    `validate-branch` retained.
  - `validate-branch` now enforces DHF item changes unconditionally (previously
    only when a spec file was present).
  - `--generate-spec` flag removed from `cr workflow intake-github-issue` and
    `intake-github-issue-ci`. Intake payloads still include `spec_generated`,
    `spec_status`, `spec_validation`, `spec_path`, `spec_json_path`, `spec_error`
    as `false`/`null` for API compatibility.
  - `implementation_notes` is now LLM-authored; the harness no longer writes a
    "Design Impact Snapshot" block to it.
  - `check_status` gate accepts `new`, `design`, and `develop` as valid states.
  - `ItemType` enum V-model defaults: traceability summary now includes an
    opt-out hint when V-model defaults are applied
    (`required_traceability: []` in `global.yaml` to disable).
  - `_item_type_dict` now returns `dt.name` (human-readable) for the `name`
    field instead of `dt.code`.

## [0.4.0] — 2026-05-13

### Changes

- **Breaking CR generation response contract redesign**
  - `ci analyze-cr`, `ci design-cr`, and `ci develop-cr` no longer emit the
    legacy `status` / `validation` / `corrections` / top-level artifact fields.
    They now return a client-facing contract built around `outcome`,
    `summary`, `timing`, `inputs`, `progress`, `steps`, `artifacts`,
    `diagnostics`, `warnings`, and `errors`.
  - `tool_error` is now a first-class outcome for hard generation failures,
    and the CI CLI exits non-zero for those runs instead of printing a false
    success summary.
  - Workflow intake adapters preserve legacy `spec_status` /
    `spec_validation` semantics so existing intake automation can continue to
    branch on those fields while the generation JSON itself moves to the new
    contract.
  - Migration: any client parsing `ci analyze-cr` / `design-cr` /
    `develop-cr` JSON must switch to the new top-level fields and read
    generated paths, change buckets, and analysis data from `artifacts`.

- **CI contract hardening for CR validation**
  - `validate-branch` now normalizes relative `--spec` paths against the repo
    root instead of assuming an already-absolute path.
  - `validate-code` now enforces `@links:` only for `test_plan.needs_new_tc`
    entries that are actual DHF item IDs, and only when the annotation appears
    on an added comment line. Free-form prose entries remain valid analysis
    output but are no longer forced through brittle exact-text annotation
    matching.
  - `validate-spec` now rejects `doc-only` specs that still list DHF impact and
    rejects `test-only` specs that propose new DHF items.
  - The CR analysis prompt now tells the model to keep `standard` when product
    code changes are needed but no DHF item updates are required, and to prefer
    real item IDs in `needs_new_tc` whenever possible.
  - Contract and unit tests now lock the help-surface for `--dhf`, the
    comment-only annotation rule, and the relative-spec-path behavior.
- **Design-phase CR impact recording**
  - `generate_design` now writes successful DHF impact back onto the CR item
    automatically: `affected_items` is updated from the validated design delta,
    and `implementation_notes` gains a managed "Design Impact Snapshot" section
    that records spec-declared new items plus actual created/updated/deleted
    DHF item IDs.
  - Generated Change Request specification documents now render
    `implementation_notes`, so the recorded design impact is visible in CR
    output without re-parsing CI logs.
- **Combined issue intake + initial spec drafting**
  - `cr workflow intake-github-issue` and `intake-github-issue-ci` now
    generate the initial spec draft by default whenever they create a new CR
    with `--write`.
  - This adds one Claude/spec-generation pass to default intake behavior.
    Use `--no-generate-spec` to opt out when a client repo wants the older,
    cheaper CR-only intake path.
  - Intake JSON now includes `spec_generated`, `spec_status`,
    `spec_validation`, `spec_path`, `spec_json_path`, and `spec_error`, so
    client repos can treat spec review as the first real approval gate without
    re-running `ci analyze-cr`.

## [0.3.7] — 2026-05-12

### Changes

- **CR triage routing** — `ci analyze-cr` now classifies CRs before writing a
  full spec, replacing the blunt `direction_fit` field with three dedicated
  front-matter fields:

  - `disposition` — required on every spec. Values: `approve`,
    `decline:out-of-scope`, `decline:duplicate`, `decline:architecture-conflict`,
    `decline:too-large`, `hold:scope-expansion`.
  - `pipeline_route` — required when `disposition: approve`. Values:
    `standard` (analyze → design → develop), `dhf-only` (no code),
    `doc-only` (no design/develop), `test-only` (no new DHF items).
  - `decline_rationale` — required string when disposition is not `approve`.
    Provides an auditable reason for the decline or hold (IEC 62304 evidence).

  For declined/held CRs only `cr_id`, `disposition`, and `decline_rationale`
  are populated; all other spec fields are skipped and not validated.

  `direction_fit` is removed. Existing specs with `direction_fit` are migrated
  transparently by `validate_spec` (legacy values map to the nearest
  `disposition`), so no manual spec updates are required. Specs that contain
  neither field fail validation and trigger the self-correction loop.

- **Enriched `proposed_new_items`** — each entry in the `proposed_new_items`
  front-matter list now supports optional `parent` and `verification_method`
  fields:

  - `parent` — ID of the existing DHF item this new item traces to (e.g.
    `SYS-012`). Validated by `validate_spec` against live DHF item IDs.
  - `verification_method` — `Inspection` or `Demonstration`; only valid for
    item types that carry a verification method in the dhfkit schema (`SYS`,
    `SOUP`). `validate_spec` rejects the field for other types.

  The `ci design-cr` prompt now receives this richer structured data so Claude
  can wire parent links and verification methods at item-creation time.

- **`validate-branch` code-change check is now opt-in** — `--code-path` must
  be passed explicitly to require that implementation files were modified. When
  omitted, the command checks only that the spec file and DHF item changes are
  present. This removes a WebTPS-specific default (`apps/`, `packages/`) that
  was incorrect for all other project layouts.

  Migration: update CI invocations that relied on the implicit default to pass
  `--code-path <dir>` explicitly, or drop the check for doc/DHF-only CRs.

---

## [0.3.6] — 2026-05-11

### Changes

- `ci analyze-cr` now emits a companion `CR-NNN-Spec.json` alongside the
  Markdown spec. The JSON contains every machine-readable front-matter field
  and is read by downstream validators in preference to re-parsing Markdown.
  The `ci analyze-cr` stdout payload gains `spec_json_path` (absolute path
  to the JSON file, or `null` if Claude wrote no spec file).

- Two new required front-matter fields are added to CR specs:
  - `proposed_new_items` — list of `{type, title}` dicts describing DHF items
    the design stage should create. `[]` is valid when no new items are needed.
  - `design_impact_summary` — a non-empty string (1–2 sentences) summarising
    the overall design impact. Required so the summary is machine-readable
    rather than buried in Markdown prose.

  Existing specs that lack these fields will fail `validate_spec` and trigger
  the self-correction loop, prompting Claude to add them.

- `ci design-cr` injects the full `CR-NNN-Spec.json` content as a structured
  block at the top of the design prompt (non-revision mode only). Claude no
  longer needs to re-parse the Markdown spec to identify affected or proposed
  items — the structured data is explicit in the prompt.

- `validate_spec`, `write_spec_json`, and `read_spec_json` are now public
  symbols in `medharness.services.spec_validation`.
- `ci analyze-cr` now also emits a structured `analysis` object in stdout,
  with `direction_fit`, `affected_items`, `proposed_new_items`,
  `design_impact_summary`, and `test_plan`, so clients do not need to
  re-parse the spec file for the most common CR-analysis fields.

- Bundled GitHub workflow templates were removed from the shipped scaffold.
  MedHarness now treats the CLI and Python services as the stable product
  surface, while repository automation is left to client repos.

- `medharness init` no longer generates `.github/workflows/*`. It still
  scaffolds DHF content and `.github/prompts/` for repo-local automation.

  Migration:
  - existing repos that previously copied bundled workflow templates should
    delete or replace those stale `.github/workflows/*` files explicitly
  - new or existing repos should move automation logic to thin repo-local
    wrappers around the CLI (`ci github-event`, `ci validate-design`,
    `ci validate-code`, `ci validate-branch`, `ci cr-status`)

- `ci github-event` now supports configurable event-to-stage and
  event-to-action mapping via CLI flags so client repos can layer their own
  automation without hardcoded MedHarness workflow assumptions.

- New `ci cr-status` command reports machine-readable CR stage and approval
  status in one JSON payload, so client automation can query whether a PR is
  approved for its current stage without re-implementing MedHarness label and
  branch conventions.

- New `ci validate-design` and `ci validate-code` commands expose the existing
  deterministic design and implementation checks as standalone CLI preflight
  steps, so client automation can catch schema, traceability, affected-item,
  and test-annotation issues before opening a PR.

- New `ci validate-branch` command checks that a single branch carries the
  expected coupled CR change set: the approved spec, product code changes, and
  DHF item YAML changes when the spec says DHF impact is expected.

---

## [0.3.5] — 2026-05-10

### Changes

- `ci design-cr` and `ci develop-cr` now run **deterministic structural
  checks before** the LLM review pass, matching the pattern already used
  by `ci analyze-cr`:
  - **design**: schema validation, required-traceability rules, orphans,
    coverage gaps, and presence of every spec `affected_items` ID — all
    via `dhfkit.api`. On failure, a fix-only LLM prompt with structured
    error lines runs once before the soft review.
  - **develop**: presence of `@links:<ID>` annotations in the diff for
    every item in the spec's `test_plan.needs_new_tc`. On failure, a
    fix-only LLM prompt asks for the missing colocated tests.
- The soft-review prompts (`cr_review_design.md`, `cr_review_code.md`)
  are trimmed to judgment questions only — schema, traceability, and
  test-annotation presence are no longer re-asked of the model. The
  prompts are augmented at runtime with a "Deterministic Checks" section
  that tells the reviewer not to re-derive what the harness already
  proved.
- `generate_design` and `generate_code` now return `corrections` and
  `validation` fields (matching `generate_spec`); `validation` is one of
  `"passed"` or `"residual_errors"` (replacing the prior placeholder
  `"not_checked"` value — consumers that string-matched the old value
  will see the new domain).
- `ci design-cr` and `ci develop-cr` stderr summaries now include the
  correction count and validation outcome, matching `ci analyze-cr`.
- `validate_code` now distinguishes git-environment failures (missing
  binary, unfetched ref, non-zero exit) from a legitimately-empty diff:
  the former emits one `field: "environment"` error so the fix-only LLM
  prompt does not waste a call asking for tests the model cannot add;
  the latter still flags missing `needs_new_tc` annotations.

### Enhanced response payload (`generate_spec` / `generate_design` / `generate_code`)

The dict returned by all three functions (and echoed as JSON by the
matching `ci analyze-cr` / `design-cr` / `develop-cr` commands) now
carries a uniform, richer shape so clients can render outcomes without
re-running validators or shelling out to git. New / changed keys:

- `stage` — one of `"spec"` / `"design"` / `"develop"`.
- `status` — `"ok"` when no residual errors remain, `"completed_with_errors"`
  otherwise (previously hard-coded `"ok"`).
- `errors` — list of structured `{field, issue, fix}` dicts surfacing the
  residual deterministic-check failures. Empty when validation passed.
- `items_changed` (design) / `files_changed` (develop) — `{created, updated,
  deleted}` lists derived from `git diff --name-status origin/main`. Item
  IDs are extracted from the YAML stem (`SYS-001` etc.).
- `started_at` (ISO 8601 UTC) and `elapsed_ms` (wall time).

Removed (placeholder fields that always returned `null` / `[]`):
`items_created`, `items_updated`, `files_written`. Use `items_changed.*`
or `files_changed.*` instead.

The `ci design-cr` / `ci develop-cr` / `ci analyze-cr` stderr summaries
now surface correction count, validation outcome, residual error count,
elapsed time, and changed-DHF / changed-files counts via a single shared
formatter.

### New helpers (`medharness.services.git`)

- `collect_path_changes(repo_root, since_ref, *paths)` —
  `{created, updated, deleted}` of file paths.
- `collect_dhf_item_changes(repo_root, since_ref)` — same shape but with
  DHF item IDs extracted from `DHF/items/.../<ID>.yaml`.

### New modules

- `medharness.services.design_validation` — `validate_design(cr_id,
  dhf_path, spec_path) -> list[dict]`
- `medharness.services.code_validation` — `validate_code(cr_id,
  dhf_path, spec_path, since_ref="origin/main") -> list[dict]`

---

## [0.3.4] — 2026-05-09

### Fixes

- `ci artifacts generate` raised `TypeError: sequence item 0: expected str
  instance, dict found` when the JUnit feed populated requirement coverage
  with test entries — `MedHarnessCore.inject_junit_results` stores each test
  as `{"name", "status"}`, but the 0.3.3 PDF formatter joined them as
  strings. The formatter now renders dicts as `"<name> [<status>]"` and
  still accepts plain strings.

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
