# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-05-03

---

## Packages

MedHarness ships two Python packages from a single repository:

| Package | CLI | Role |
|---------|-----|------|
| `medharness` | `medharness` | Orchestration, scaffolding, CI gates, CR workflows, DHF operations |
| `dhfkit` | `dhfkit` / `dhf` | DHF engine: item CRUD, lifecycle, traceability, document generation; standalone use without `medharness` |

### `medharness` owns

- CLI surface and user-facing onboarding (`medharness init`)
- CI gate commands (`ci test-coverage`, `ci dhf-validate`, `ci evidence bundle`)
- CR workflow orchestration (`cr workflow`, `cr check-status`, `cr intake`)
- Product repo file generation (`CLAUDE.md`, `.gitignore`)
- DHF repo scaffolding from bundled templates
- Adapter protocol for pluggable DHF backends

### `dhfkit` owns

- Item CRUD and lifecycle state machine
- Project config loading and doc-type schema rendering
- Required traceability rules and coverage checks
- Document generation (Jinja2 → Markdown → PDF)
- JUnit XML parsing and CI artifact fetching
- Git-backed YAML repository layer (loader/saver)
- Result store for test result history

### Boundary rules

- `medharness` may import from `dhfkit`
- `dhfkit` MUST NOT import from `medharness`
- `dhfkit` can be used standalone without `medharness`

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
│   └── prompts/               # Optional prompt templates for repo-local automation
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
│   └── prompts/                  # Optional prompt files; automation is client-owned
└── README.md
```

The generated DHF repo does not contain `dhfkit/` or `medharness/` source code. Users install MedHarness separately and run `medharness --dhf DHF ...` against the generated DHF directory.

### Placeholder substitution

| Placeholder | Example value |
|-------------|---------------|
| `{{project_name}}` | `Insulin Pump Firmware` |
| `{{product_repo}}` | `acme-medical/insulin-pump` |
| `{{product_repo_name}}` | `insulin-pump` |
| `{{github_org}}` | `acme-medical` |
| `{{dhf_repo_name}}` | `insulin-pump-dhf` |
| `{{compliantflow_version}}` | `0.3.5` |
| `{{compliantflow_repo}}` | `itercharles/MedHarness` |
| `{{primary_test_tool}}` | `pytest` |

---

## DHF Repo Lifecycle

| Event | Action |
|-------|--------|
| New project | `medharness init` creates the DHF repo |
| Feature or bugfix | Open a CR, run the CR workflow, merge to main |
| New MedHarness release | Re-scaffold into a new directory, apply diff selectively — never overwrite existing DHF content |
| Regenerate documents | `medharness --dhf DHF dhf doc generate ALL` — run after item changes or template updates |
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
| Integration | `tests/integration/` | Package integration: init, DHF facade, CR workflows |
| Contract | `tests/contract/` | Public contracts: CLI, scaffold structure, example smoke |
| Engine | `dhfkit/tests/` | dhfkit-specific: CRUD, validation, document generation |

This repo does not use `@links`/`@test_id` metadata or `ci test-coverage` for its own governance. Those features are available to scaffolded user DHF repos.
