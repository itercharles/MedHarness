# Architecture

> **Stability:** Stable
> **Last reviewed:** 2026-05-16

---

## Packages

MedHarness ships two Python packages from a single repository:

| Package | CLI | Role |
|---------|-----|------|
| `medharness` | `medharness` | Orchestration, scaffolding, CI gates, CR workflows, DHF operations |
| `dhfkit` | `dhfkit` / `dhf` | DHF engine: item CRUD, lifecycle, traceability, document generation; standalone use without `medharness` |

### `medharness` owns

- CLI surface and user-facing onboarding (`medharness init`)
- CI gate commands (`ci dhf-validate`, `ci test-coverage`, `ci validate-branch`, `ci validate-code`, `ci evidence bundle`)
- AI-assisted CR generation (`ci generate-dhf`, `ci develop-cr`)
- SOUP management and release baseline (`ci soup-sync`, `ci release-baseline`)
- Approval gating and stage management (`ci approve-gate`, `ci advance-stage`, `ci cr-status`, `ci parse-approval`)
- CR workflow orchestration (`cr workflow`, `cr check-status`)
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
| `{{primary_test_tool}}` | `pytest` |

---

## DHF Item Type Model

Each DHF item has a type (CR, SYS, SRS, SWDD, …) that determines its schema,
lifecycle rules, and valid traceability links. The types form a structured graph.

### Item types

| Code | Name | Role | One item per… |
|------|------|------|---------------|
| `UC` | Use Case | `use_case` | User goal or operating scenario |
| `CRS` | Customer Requirement | `customer_requirement` | Stakeholder need |
| `SYS` | System Requirement | `system_requirement` | System-level behavioural obligation |
| `SYSARCH` | System Architecture | `architecture` | System-level design decision for a SYS requirement |
| `SRS` | Software Requirement | `software_requirement` | Software-level behavioural obligation |
| `MODULE` | Software Module | `software_module` | Software unit defined in the architecture decomposition |
| `SWDD` | Software Detailed Design | `design_detail` | Design decisions for an SRS requirement within a module |
| `RISK` | Risk | `risk` | Identified hazard or hazardous situation |
| `RCM` | Risk Control Measure | `risk_control` | Mitigation for a risk, implemented as a system requirement |
| `CR` | Change Request | `change_request` | Proposed change driving a DHF update cycle |
| `SOUP` | Software of Unknown Provenance | `soup` | Third-party dependency tracked for IEC 62304 §5.3.3 |
| `REL` | Release | `release` | Software release record (IEC 62304 §9) |
| `DEF` | Defect | `defect` | Tracked problem or non-conformance |

### Traceability links

Links between items are directional. The table below shows the canonical link
field, the direction it is written, and what each relationship means.

| Link field | Written on | Points to | Meaning |
|------------|-----------|-----------|---------|
| `derives_from` | CRS | UC | Customer requirement derives from a use case |
| `satisfies` | SYS | CRS | System requirement satisfies a customer requirement |
| `design` | SYSARCH | SYS | Architecture item designs a system requirement |
| `derives_from` | SRS | SYS | Software requirement derives from a system requirement |
| `module` | SWDD | MODULE | Detailed design belongs to this software module |
| `implements` | SWDD | SRS | Detailed design implements a software requirement |
| `mitigates` | RCM | RISK | Risk control measure mitigates a risk |
| `implements` | RCM | SYS | Risk control measure is implemented as a system requirement |

### Design layer roles

**SYSARCH — per SYS requirement.** Each SYSARCH item records the system-level
design decision for one SYS requirement: which module receives an output, what
protocol is used, how the boundary is drawn. SYSARCH items are
requirement-oriented, not module-oriented.

**MODULE — per software unit.** MODULE items define the software decomposition
declared in the architecture document overview. Each MODULE item describes a
unit's responsibility, key interfaces, and internal structure. MODULE items are
the module-oriented anchor; they are not tied to individual requirements.

**SWDD — per SRS requirement, grouped by module.** Each SWDD item records the
design decisions for one SRS requirement (or a small cluster of closely related
ones) within a specific module. SWDD items are requirement-oriented like SYSARCH,
but they belong to a MODULE. The combined picture — MODULE overview + its SWDD
items — forms the Software Design Document for that module.

### Coverage rules (defaults)

The traceability validator enforces coverage in both directions using these
default matrices. Projects may extend or restrict them via `global.yaml`.

| Matrix | Meaning |
|--------|---------|
| UC → CRS | Every use case is addressed by at least one customer requirement |
| CRS → SYS | Every customer requirement is allocated to at least one system requirement |
| SYS → SRS | Every system requirement is refined into at least one software requirement |
| SRS → SWDD | Every software requirement has at least one detailed design item |
| SYS → SYSARCH | Every system requirement has at least one architectural design |
| MODULE → SWDD | Every defined module has at least one detailed design item |
| RISK → RCM | Every identified risk has at least one control measure |

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

---

## CR Workflow

### Two-phase flow

Every CR moves through two AI-assisted phases on a single branch and PR:

```
generate-dhf  →  (design PR reviewed + approved)  →  develop-cr
```

**`generate-dhf`**

1. Triage — checks for duplicate, out-of-scope, architecture-conflict, or too-large
2. V-model cascade — creates/updates DHF items top-down: CR → CRS → SYS → {SYSARCH, RISK, RCM} → SRS → SWDD. Each SWDD item links to an existing MODULE and implements the relevant SRS items. Reads relevant source modules before writing SWDD items so the design reflects the actual codebase.
3. Implementation plan — writes a structured implementation plan (overview, current state, changes required, steps, edge cases, tests) into `implementation_notes` on the CR item
4. Deterministic validation — `dhf validate schema` + `dhf validate traceability`; self-corrects if errors remain

**`develop-cr`**

1. Reads `implementation_notes` as the primary implementation spec (reviewed and approved with the design PR)
2. Implements code following the plan; reads SWDD items for module-level design decisions
3. Annotates tests with `@links:<ITEM_ID>`, runs `medharness ci test-coverage` against JUnit output, adds missing annotations until all requirements are covered
4. Reconciles `implementation_notes` and SWDD items if the implementation deviated from the plan

### CR lifecycle states

| State | Set by | Meaning |
|-------|--------|---------|
| `new` | Intake | CR created |
| `design` | `generate-dhf` | Design phase started |
| `develop` | `develop-cr` | Implementation phase started |
| `completed` | PR merge | Code merged to main |
| `cancelled` | PR close | PR closed without merging |
| `rejected` | `generate-dhf` triage | Out-of-scope / duplicate / too large |

State transitions are not enforced as execution gates — the auto workflow proceeds regardless. States are recorded for traceability.

### CR Generation Service Topology

The CR-generation path in `medharness.services` is split by responsibility:

- `cr_generation.py` — stage orchestration, Claude invocation, PR-feedback retrieval; public entry points are `generate_dhf` and `generate_code`
- `prompt_assembly.py` — prompt-template loading and composition; injects pre-computed DHF context (item lists, traceability graph, coverage gaps) into each prompt
- `cr_impact.py` — writes `affected_items` back onto the CR item after `generate-dhf` completes; `implementation_notes` is LLM-authored and not overwritten by the harness
- `design_validation.py` — deterministic post-design checks; only catches schema, traceability, and DHF-validation failures

This split is internal structure, not a public import contract. The public behavior is the CLI and JSON response contracts documented in the CHANGELOG and enforced by consumer-side contract tests.
