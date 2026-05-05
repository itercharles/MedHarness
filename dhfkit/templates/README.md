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
│   │   ├── 04_swdd/          # Detailed Design (SWDD-NNN.yaml)
│   │   ├── 05_sysarch/       # System Architecture (SYSARCH-NNN.yaml)
│   │   ├── 06_cr/            # Change Requests (CR-NNN.yaml)
│   │   ├── 07_rel/           # Releases (REL-NNN.yaml)
│   │   ├── 08_soup/          # SOUP items (SOUP-NNN.yaml)
│   │   ├── 09_risk/          # Risk items (RISK-NNN.yaml)
│   │   ├── 10_rcm/           # Risk Control Measures (RCM-NNN.yaml)
│   │   └── 11_def/           # Defects (DEF-NNN.yaml)
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
