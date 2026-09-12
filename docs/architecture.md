# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-05-24

---

## Packages

MedHarness ships two Python packages from a single repository:

| Package | CLI | Role |
|---------|-----|------|
| `medharness` | `medharness` | AI harness: traceability analysis over the item set, scaffolding, verification, change workflows, approval flow |
| `dhfkit` | `dhfkit` / `dhf` | DHF storage: item CRUD, lifecycle, link integrity, document generation, SOUP sync, release baseline |

### `medharness` owns

- Traceability analysis over the whole item set — coverage chains, required
  links, link cycles, risk chains, which risks a change touches
  (`services/traceability.py`)
- CLI surface and user-facing onboarding (`medharness init`)
- Verification commands (`verify dhf`, `verify tests`, `verify branch`, `evidence bundle`)
- AI-assisted CR generation (`change plan`, `change implement`)
- Approval and stage management (`approval check`, `change advance`, `change status`, `approval parse`)
- CR workflow orchestration (`cr workflow`, `cr check-status`)
- DHF repo scaffolding from bundled templates (`medharness init`, `medharness upgrade`)
- Environment and setup diagnostics (`medharness doctor`)
- Machine-readable description of the gates (`medharness gates`)
- Adapter protocol for pluggable DHF backends

### `dhfkit` owns

- Item CRUD and lifecycle state machine
- Project config loading and doc-type schema rendering
- Referential integrity of stored links (`validate links`)
- Document generation (Jinja2 → Markdown → PDF)
- JUnit XML parsing and CI artifact fetching
- Git-backed YAML repository layer (loader/saver)
- Result store for test result history
- SOUP manifest synchronisation (`soup-sync`)
- Release baseline builder (`release-baseline`)
- CycloneDX SBOM serialisation from the SOUP register (`sbom`)
- Approval records as DHF items (`approval import`, `approval show`)

### The line between them

`dhfkit` stores and retrieves records. `medharness` analyses them.

A change-controlled organisation may already keep its DHF in Jira, Azure DevOps
or a system of its own, and those manage a single item well. What none of them
do is take the items together and ask whether the V-model holds — whether every
system requirement gives rise to a software one, whether a chain closes back on
itself, which risks a change touches. That analysis is what this project is for,
so it cannot live in one storage implementation.

The test is what a store already answers on its own:

| question | whose |
|---|---|
| is this item well-formed | store |
| do two files claim one ID | store |
| does this link name an item that exists | store |
| is every SYS covered by an SRS | **medharness** |
| does a traceability chain cycle | **medharness** |
| which risks does this change touch | **medharness** |
| are the required links present for this doc type | **medharness** |

The last one is the least obvious: "every SRS must derive from a SYS" is a
modelling decision about the V-model, not a storage constraint. Jira will not
enforce it either.

Analysis takes items as data — `medharness.services.traceability` receives a
list of dicts and a config, never a path or a loader — so it works against any
adapter satisfying `medharness/adapters/protocol.py`.

### One exception, deliberately

`medharness init` and `medharness upgrade` write DHF files directly — the config
files, the spec templates, the plan documents a new project starts from.

That is not analysis reaching into storage. Those commands create and maintain
the *repository skeleton*: they bring a DHF into existence and keep its
scaffold current across versions. `dhfkit` manages records; it does not manage
the shape of the repository that holds them, and giving it a "write my config
file" API to satisfy a rule would put storage in the business of scaffolding.

Everywhere else, medharness asks the store. `verify classification` reads plan documents
through `list_documents("plans")` and `get_document()`; `upgrade` reads the
project name through `ProjectConfig.load()` rather than the regex it used to
apply to global.yaml — which took a trailing comment as part of the name.

`tests/guards/test_storage_access_is_bounded.py` holds the exception to the two
scaffold modules.

### Boundary rules

- `medharness` may import from `dhfkit`
- `dhfkit` MUST NOT import from `medharness`
- `dhfkit` can be used standalone without `medharness`
- `medharness` uses `dhfkit`'s **public** surface. Standalone use means `dhfkit`
  has a contract, and a consumer pinned to an underscore has none — ten sites
  read `adapter._config` before this rule was written down and checked.

`tests/guards/test_package_boundary.py` enforces the last two; the import
direction was already guarded, what a consumer may touch was not.

---

## Scaffold Model

`medharness init` copies assets from `dhfkit/templates/` (bundled with the package) to create a self-contained DHF repository.

### Template source

```
dhfkit/templates/
├── config/                    # Doc type definitions (global.yaml + doc_types/*.yaml)
├── specs/                     # Jinja2 templates for document generation (*.md.j2)
│   └── styles/                # PDF CSS stylesheet
├── plans/                     # Plan document templates
├── github/
│   ├── prompts/               # AI agent prompt templates
│   └── workflows/             # DHF-side CI workflows
├── AI-harness/
│   └── context.md             # Product context template for AI agents
└── README.md                  # DHF repo starter README
```

### Generated DHF repo structure

```
<dhf-repo>/
├── DHF/
│   ├── config/
│   │   ├── global.yaml           # Project name, lifecycle, traceability matrices
│   │   └── doc_types/            # One YAML per doc type
│   ├── documents/
│   │   ├── specs/                # Jinja2 templates + default.css
│   │   └── plans/                # Plan documents
│   ├── items/                    # One subdir per doc type (ready for YAML items)
│   └── test-results/             # .gitkeep (ready for JUnit evidence)
├── AI-harness/
│   └── context.md                # Product context for AI agents
├── .github/
│   ├── prompts/                  # AI agent prompts for CR workflows
│   └── workflows/                # DHF-side CI: schema validation, CR automation
└── README.md
```

The generated DHF repo does not contain `dhfkit/` or `medharness/` source code. Install MedHarness separately. Use `dhfkit --dhf DHF ...` for data operations (item CRUD, validate, docs); use `medharness --dhf DHF change ...`, `verify ...`, and `evidence ...` for AI-assisted change workflows and validation.

### Placeholder substitution

| Placeholder | Example value |
|-------------|---------------|
| `Medharness` | `Insulin Pump Firmware` |
| `{{product_repo}}` | `acme-medical/insulin-pump` |
| `{{product_repo_name}}` | `insulin-pump` |
| `{{github_org}}` | `acme-medical` |
| `{{dhf_repo_name}}` | `insulin-pump-dhf` |
| `pytest` | `pytest` |

---

## DHF Repo Lifecycle

| Event | Action |
|-------|--------|
| New project | `medharness init` creates the DHF repo |
| Feature or bugfix | Open a CR, run the CR workflow, merge to main |
| New MedHarness release | Re-scaffold into a new directory, apply diff selectively — never overwrite existing DHF content |
| Regenerate documents | `dhfkit --dhf DHF doc generate ALL` — run after item changes or template updates |
| Product retirement | Archive the DHF repo in Git with an archival date in the README; preserve for regulatory audit |

### Product repo vs DHF repo

| Aspect | Product repo | DHF repo |
|--------|-------------|----------|
| Contains | Source code, tests, build config | Requirements, architecture, risk, traceability |
| CI | Client-owned | Client-owned |
| Updated | Per feature/bugfix | Per CR-driven change |
| Archival | With product retirement | Must be preserved for regulatory audit |

---

## Test Organization

| Layer | Directory | Scope |
|-------|-----------|-------|
| Unit | `tests/unit/` | Pure logic: parsers, config, lifecycle, traceability |
| Guards | `tests/guards/` | The repo about itself: import boundaries, documented commands, packaging, mock contracts |
| Integration | `tests/integration/` | Package integration: init, DHF facade, CR workflows |
| Contract | `tests/contract/` | Public contracts: CLI, scaffold structure, example smoke |
| Engine | `dhfkit/tests/` | dhfkit-specific: CRUD, validation, document generation |

This repo does not use `@links`/`@test_id` metadata or `verify tests` for its own governance. Those features are available to scaffolded user DHF repos.

---

## CR Workflow

### Two-phase flow

Every CR moves through two AI-assisted phases on a single branch and PR:

```
change plan  →  (design PR reviewed + approved)  →  change implement
```

**`change plan`**

1. Triage — checks for duplicate, out-of-scope, architecture-conflict, or too-large; writes `triage_result` (verdict, complexity, affected_subsystems, notes) onto the CR item
2. V-model cascade — creates/updates DHF items top-down: CR → CRS → SYS → {SYSARCH, RISK, RCM} → SRS → SWDD. Each SWDD item links to an existing MODULE and implements the relevant SRS items. Reads relevant source modules before writing SWDD items so the design reflects the actual codebase. Writes `affected_risk_items` (list of RISK/RCM IDs relevant to this CR, or `[]`) onto the CR item.
3. Implementation plan — writes a structured implementation plan (overview, current state, changes required, steps, edge cases, tests) into `implementation_notes` on the CR item
4. Deterministic validation — `dhfkit validate schema` + `medharness verify dhf` for the stored data, `medharness verify dhf` for the analysis; self-corrects if errors remain
5. Design review (soft) — reviews every changed DHF item for necessity, product/technical strategy alignment, and SWDD + implementation note clarity. Writes verdict and issues to `docs/reviews/<CR>-Design-Review.md`. If **Needs Revision**, a fix pass runs and the review repeats up to three cycles.

**`change implement`**

1. Reads `implementation_notes` as the primary implementation spec (reviewed and approved with the design PR)
2. Implements code following the plan; reads SWDD items for module-level design decisions
3. Annotates tests with `@links:<ITEM_ID>`, runs `medharness verify tests` against JUnit output, adds missing annotations until all requirements are covered
4. Reconciles `implementation_notes` and SWDD items if the implementation deviated from the plan
5. Code review (soft) — reviews the implementation for completeness, test depth, scope, and conventions. Verdict is returned inline (no file written). If **Needs Revision**, a fix pass runs and the review repeats up to three cycles.

### CR lifecycle states

| State | Set by | Meaning |
|-------|--------|---------|
| `new` | Intake | CR created |
| `design` | `change plan` | Design phase started |
| `develop` | `change implement` | Implementation phase started |
| `completed` | PR merge | Code merged to main |
| `cancelled` | PR close | PR closed without merging |
| `rejected` | `change plan` triage | Out-of-scope / duplicate / too large |

State transitions are not enforced as execution gates — the auto workflow proceeds regardless. States are recorded for traceability.

### CR Generation Service Topology

The CR-generation path in `medharness.services` is split by responsibility:

- `cr_generation.py` — stage orchestration, LLM invocation, PR-feedback retrieval; public entry points are `generate_dhf` and `generate_code`. Both return a `design_review` / `code_review` field with per-cycle `{verdict, issues}` data and a human-readable `narrative` list. Each workflow stage resolves its own `LLMConfig` from `MEDHARNESS_{DESIGN|DESIGN_REVIEW|DEVELOP|CODE_REVIEW}_MODEL` env vars; supported providers are `anthropic` (Claude CLI, default), `openai`, and `deepseek`.
- `prompt_assembly.py` — prompt-template loading and composition; injects pre-computed DHF context (item lists, traceability graph, coverage gaps) into each prompt
- `cr_impact.py` — writes `affected_items` back onto the CR item after `change plan` completes; `implementation_notes` is LLM-authored and not overwritten by the harness
- `design_validation.py` — deterministic post-design checks; only catches schema, traceability, and DHF-validation failures

This split is internal structure, not a public import contract. The public behavior is the CLI and JSON response contracts documented in the CHANGELOG and enforced by consumer-side contract tests.
