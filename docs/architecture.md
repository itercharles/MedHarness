# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-05-03

---

## Packages

CompliantFlow ships two Python packages from a single repository:

| Package | CLI | Role |
|---------|-----|------|
| `compliantflow` | `compliantflow` | Orchestration, scaffolding, CI gates, CR workflows, DHF operations |
| `dhf_util` | `dhf` | DHF engine: item CRUD, lifecycle, traceability, document generation; standalone use without `compliantflow` |

### `compliantflow` owns

- CLI surface and user-facing onboarding (`compliantflow init`)
- CI gate commands (`ci test-coverage`, `ci dhf-validate`, `ci evidence bundle`)
- CR workflow orchestration (`cr workflow`, `cr check-status`, `cr intake`)
- Product repo file generation (CLAUDE.md, engineering-control.yml, cr-complete.yml, review-pr.yml)
- DHF repo scaffolding from bundled templates
- Adapter protocol for pluggable DHF backends

### `dhf_util` owns

- Item CRUD and lifecycle state machine
- Project config loading and doc-type schema rendering
- Required traceability rules and coverage checks
- Document generation (Jinja2 → Markdown → PDF)
- JUnit XML parsing and CI artifact fetching
- Git-backed YAML repository layer (loader/saver)
- Result store for test result history

### Boundary rules

- `compliantflow` may import from `dhf_util`
- `dhf_util` MUST NOT import from `compliantflow`
- `dhf_util` can be used standalone without `compliantflow`

---

## Scaffold Model

`compliantflow init` copies assets from `dhf_util/templates/` (bundled with the package) to create a self-contained DHF repository.

### Template source

```
dhf_util/templates/
├── config/                    # Doc type definitions (global.yaml + doc_types/*.yaml)
├── specs/                     # Jinja2 templates for document generation (*.md.j2)
│   └── styles/                # PDF CSS stylesheet
├── plans/                     # Plan document templates
├── github/
│   ├── prompts/               # LLM prompt templates for CR workflows
│   └── workflows/
│       ├── dhf/               # DHF repo CI workflows (copied to DHF repo)
│       └── product/           # Product repo workflows (written to product repo)
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
├── .github/
│   └── workflows/                # DHF-side CI from templates/github/workflows/dhf/
└── README.md
```

The generated DHF repo does not contain `dhf_util/` or `compliantflow/` source code. Users install CompliantFlow separately and run `compliantflow dhf` against the generated DHF directory.

### Placeholder substitution

| Placeholder | Example value |
|-------------|---------------|
| `{{project_name}}` | `Insulin Pump Firmware` |
| `{{product_repo}}` | `acme-medical/insulin-pump` |
| `{{product_repo_name}}` | `insulin-pump` |
| `{{github_org}}` | `acme-medical` |
| `{{dhf_repo_name}}` | `insulin-pump-dhf` |
| `{{compliantflow_version}}` | `0.1.0` |
| `{{compliantflow_repo}}` | `itercharles/CompliantFlow` |
| `{{primary_test_tool}}` | `pytest` |

---

## DHF Repo Lifecycle

| Event | Action |
|-------|--------|
| New project | `compliantflow init` creates the DHF repo |
| Feature or bugfix | Open a CR, run the CR workflow, merge to main |
| New CompliantFlow release | Re-scaffold into a new directory, apply diff selectively — never overwrite existing DHF content |
| Regenerate documents | `compliantflow --dhf DHF dhf doc generate ALL` — run after item changes or template updates |
| Product retirement | Archive the DHF repo in Git with an archival date in the README; preserve for regulatory audit |

### Product repo vs DHF repo

| Aspect | Product repo | DHF repo |
|--------|-------------|----------|
| Contains | Source code, tests, build config | Requirements, architecture, risk, traceability |
| CI | Build, test, evidence gates | Structural validation, CR checks |
| Updated | Per feature/bugfix | Per CR-driven change |
| Archival | With product retirement | Must be preserved for regulatory audit |

---

## Test Organization

| Layer | Directory | Scope |
|-------|-----------|-------|
| Unit | `tests/unit/` | Pure logic: parsers, config, lifecycle, traceability |
| Integration | `tests/integration/` | Package integration: init, DHF facade, CR workflows |
| Contract | `tests/contract/` | Public contracts: CLI, scaffold structure, example smoke |
| Engine | `dhf_util/tests/` | dhf_util-specific: CRUD, validation, document generation |

This repo does not use `@links`/`@test_id` metadata or `ci test-coverage` for its own governance. Those features are available to scaffolded user DHF repos.
