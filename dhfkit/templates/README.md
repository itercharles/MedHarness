# DHF — Design History File

# DHF — Design History File for {{project_name}}

This is the DHF (Design History File) for {{project_name}}, scaffolded by
[MedHarness](https://github.com/itercharles/MedHarness).

> **This repo contains starter sample content.** All items, documents, and
> plans are placeholder examples. Replace them with your project's real
> requirements, architecture, risks, and change records before using this
> repository for a regulated product.

## Next Steps After Scaffolding

1. Replace all sample items under `DHF/items/` with your project's actual requirements
2. Adapt documents under `DHF/documents/plans/` to your project's processes
3. Run `medharness --dhf DHF dhf validate schema` to verify
4. Commit and push to start the CR-driven development workflow

## Directory Layout

```
├── DHF/
│   ├── items/                # One YAML file per requirement/risk/CR item
│   │   ├── 00_uc/            # Use Cases (UC-NNN.yaml)
│   │   ├── 01_crs/           # Customer Requirements (CRS-NNN.yaml)
│   │   ├── 02_sys/           # System Requirements (SYS-NNN.yaml)
│   │   ├── 03_srs/           # Software Requirements (SRS-NNN.yaml)
│   │   ├── 04_modules/       # Software Modules (MODULE-NNN.yaml)
│   │   ├── 05_swdd/          # Detailed Design (SWDD-NNN.yaml)
│   │   ├── 06_sysarch/       # System Architecture (SYSARCH-NNN.yaml)
│   │   ├── 07_cr/            # Change Requests (CR-NNN.yaml)
│   │   ├── 08_rel/           # Releases (REL-NNN.yaml)
│   │   ├── 09_soup/          # SOUP items (SOUP-NNN.yaml)
│   │   ├── 10_risk/          # Risk items (RISK-NNN.yaml)
│   │   ├── 11_rcm/           # Risk Control Measures (RCM-NNN.yaml)
│   │   └── 12_def/           # Defects (DEF-NNN.yaml)
│   ├── config/               # Project configuration
│   │   ├── global.yaml       # Global settings (project name, lifecycle states)
│   │   └── doc_types/        # One YAML per document type (SYS.yaml, CR.yaml, …)
│   ├── test-results/
│   │   └── results.yaml      # Automated test result records (TC items)
│   └── documents/
│       ├── plans/            # Planning documents (development_plan.md, integration_plan.md, …)
│       └── specs/            # Generated specification documents (Markdown) + Jinja2 templates (.j2)
├── AI-harness/
│   └── context.md            # Shared context for AI agents (project overview, scope, constraints)
├── .github/
│   ├── prompts/              # AI agent prompts used by CR workflows (cr-analyze, cr-develop)
│   └── workflows/            # DHF-side CI: schema validation, CR automation
└── README.md
```

## DHF Item Type Model

Items are organized into 13 standard types that follow the V-model hierarchy. Each type has a
fixed code prefix and a defined role in the design and traceability chain.

| Code | Name | One item per… |
|------|------|---------------|
| `UC` | Use Case | User goal or operating scenario |
| `CRS` | Customer Requirement | Stakeholder need |
| `SYS` | System Requirement | System-level behavioural obligation |
| `SRS` | Software Requirement | Software-level behavioural obligation |
| `MODULE` | Software Module | Software unit defined in the architecture decomposition |
| `SWDD` | Software Detailed Design | Design decisions for an SRS requirement within a module |
| `SYSARCH` | System Architecture | System-level design decision for a SYS requirement |
| `RISK` | Risk | Identified hazard or hazardous situation |
| `RCM` | Risk Control Measure | Mitigation for a risk, implemented as a system requirement |
| `CR` | Change Request | Proposed change driving a DHF update cycle |
| `SOUP` | SOUP | Third-party dependency tracked for IEC 62304 §5.3.3 |
| `REL` | Release | Software release record (IEC 62304 §9) |
| `DEF` | Defect | Tracked problem or non-conformance |

### Traceability Links

Items reference each other through typed link fields. All links are written on the child item
and point upward to the parent.

| Link field | Written on | Points to | Meaning |
|------------|-----------|-----------|---------|
| `derives_from` | CRS | UC | Customer requirement derives from a use case |
| `satisfies` | SYS | CRS | System requirement satisfies a customer requirement |
| `design` | SYSARCH | SYS | Architecture item records the design decision for a SYS requirement |
| `derives_from` | SRS | SYS | Software requirement derives from a system requirement |
| `module` | SWDD | MODULE | Detailed design belongs to this software module |
| `implements` | SWDD | SRS | Detailed design implements a software requirement |
| `mitigates` | RCM | RISK | Risk control measure mitigates a risk |
| `implements` | RCM | SYS | Risk control measure is implemented as a system requirement |

### Design Layer: SYSARCH / MODULE / SWDD

Three item types together describe the software design:

- **SYSARCH** — one per SYS requirement. Records the system-level design decision for that
  specific requirement (which module handles it, what protocol is used, where the boundary falls).
  Requirement-oriented, not module-oriented.
- **MODULE** — one per software unit. Defines each unit's responsibility, key interfaces, and
  internal structure. These are declared in the architecture overview, not tied to individual
  requirements.
- **SWDD** — one per SRS requirement, grouped under a MODULE. Records detailed design decisions
  within a specific module. Must carry both `implements` (SRS ID) and `module` (MODULE ID).
  The combined picture — MODULE overview + its SWDD items — forms the Software Design Document for
  that module.

### AI-harness/context.md

This is the shared memory file for AI agents. The `cr-analyze` and `cr-develop` workflows
read it before running Claude. Keep it updated after significant architecture changes,
scope decisions, or regulatory classification updates.

The file includes:

- Product overview and regulatory class
- Architecture decisions that constrain implementation
- Scope boundaries (in/out of scope)
- Known platform or integration constraints
- Active CR list (maintained by workflows)

CI agents (`cr-analyze`, `cr-develop`) include `AI-harness/context.md` as one of their
primary inputs alongside the CR spec and DHF item list.


> **Note:** `dhfkit` is distributed as part of the MedHarness package.
> Install it with `pip install medharness`.

## Config Format

Project configuration is split into two levels:

**`config/global.yaml`** — project-wide settings:
```yaml
project_name: {{project_name}}
global_lifecycle:
  states:
    - name: draft
      is_stable: false
    - name: approved
      is_stable: true
```

**`config/doc_types/<TYPE>.yaml`** — one file per document type:
```yaml
code: SYS
prefix: "SYS-"
  directory: "02_sys"
has_verification: true
properties:
  - name: title
    type: string
    required: true
  - name: derives_from
    type: list
    required: false
```

Document types with an explicit `lifecycle` block (CR, REL, DEF) have state-machine transitions. All other types use the GitOps approval model (no `status` field).

## GitOps Approval Model

Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM) have **no `status` field**. Approval is implicit from Git history:

| Git state | Meaning |
|-----------|---------|
| On `main` branch | Approved |
| On feature branch | Draft / under review |
| Deleted from repo | Retired |

This means every PR review is a formal approval event, with a complete Git audit trail.

## Test Results

TC (test case) items are **not stored as YAML files** — they live exclusively in `test-results/results.yaml` managed by `ResultStore`. There is no doc type definition for TC in the config.

After test import, `verification_status` is recomputed for each linked requirement item:
- `verified` — all linked TCs pass
- `failed` — at least one linked TC fails
- `not_verified` — no test results linked

## DHF CLI

The `dhfkit` package (installed via `pip install medharness`) exposes a data-management CLI for item CRUD, schema validation, document generation, and reading test results.

```bash
# From the DHF repo root
medharness dhf --help

# Item operations
medharness --dhf DHF dhf item list --type SYS
medharness --dhf DHF dhf item get SYS-001
medharness --dhf DHF dhf item create --type SYS --data '{"title": "My req"}'
medharness --dhf DHF dhf item update SYS-001 --data '{"title": "Updated"}'
medharness --dhf DHF dhf item delete SYS-001

# Lifecycle transitions (CR, REL, DEF only)
medharness --dhf DHF dhf item transitions CR-001
medharness --dhf DHF dhf item transition CR-001 approved --by "Alice"

# Schema validation
medharness --dhf DHF dhf validate schema

# Document generation
medharness --dhf DHF dhf doc generate ALL
medharness --dhf DHF dhf doc generate SYS

# Test result reads
medharness --dhf DHF dhf test list
medharness --dhf DHF dhf test list --status FAIL
```

## What Lives Outside DHF

| Concern | Location | Reason |
|---------|----------|--------|
| Test framework adapter | Product repo's `tests/conftest.py` | pytest-specific; not part of DHF |
| Virtual environment | `.venv/` (product repo root) | Standard Python convention |

The `dhfkit` package is bundled with MedHarness and can be used standalone or replaced by any backend that implements the `DHFAdapter` protocol.
