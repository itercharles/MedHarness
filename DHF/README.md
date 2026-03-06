# DHF — Design History File

This directory is the data layer for CompliantFlow. It stores all regulated artifacts — requirements, risks, change requests, test results, and generated documents — as plain YAML files tracked in Git.

## Directory Layout

```
DHF/
├── items/                  # One YAML file per requirement/risk/CR item
│   ├── 01_uc/              # Use Cases (UC-NNN.yaml)
│   ├── 02_crs/             # Customer Requirements (CRS-NNN.yaml)
│   ├── 03_sys/             # System Requirements (SYS-NNN.yaml)
│   ├── 04_srs/             # Software Requirements (SRS-NNN.yaml)
│   ├── 05_sysarch/         # System Architecture (SYSARCH-NNN.yaml)
│   ├── 06_swdd/            # Detailed Design (SWDD-NNN.yaml)
│   ├── 07_risk/            # Risk items (RISK-NNN.yaml)
│   ├── 08_rcm/             # Risk Control Measures (RCM-NNN.yaml)
│   └── 09_cr/              # Change Requests (CR-NNN.yaml)
├── config/                 # Project configuration
│   ├── global.yaml         # Global settings (project name, lifecycle states)
│   └── doc_types/          # One YAML per document type (SYS.yaml, CR.yaml, …)
├── test-results/
│   └── results.yaml        # Automated test result records (TC items)
├── documents/
│   └── specifications/     # Generated specification documents (Markdown)
└── utils/                  # DHF data-layer Python package (importable as `utils`)
    ├── models/             # Pydantic models: Item, ProjectConfig, DocTypeConfig
    ├── repository/         # ItemLoader, ItemSaver, GitRepository
    ├── result_store.py     # Test result persistence (results.yaml)
    ├── junit_parser.py     # JUnit XML → ExecutionResult (framework-agnostic)
    ├── document_generation.py  # Markdown specification generation
    └── cli.py              # DHF CLI entry point (python -m utils)
```

## Config Format

Project configuration is split into two levels:

**`config/global.yaml`** — project-wide settings:
```yaml
project_name: CompliantFlow
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
directory: "03_sys"
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

The `utils` package exposes a data-management CLI for item CRUD, schema validation, document generation, and reading test results.

```bash
# From the repo root
PYTHONPATH=src:DHF python -m utils --help

# Item operations
PYTHONPATH=src:DHF python -m utils item list --type SYS
PYTHONPATH=src:DHF python -m utils item get SYS-001
PYTHONPATH=src:DHF python -m utils item create --type SYS --data '{"title": "My req"}'
PYTHONPATH=src:DHF python -m utils item update SYS-001 --data '{"title": "Updated"}'
PYTHONPATH=src:DHF python -m utils item delete SYS-001

# Schema validation
PYTHONPATH=src:DHF python -m utils validate schema

# Document generation
PYTHONPATH=src:DHF python -m utils doc generate ALL
PYTHONPATH=src:DHF python -m utils doc generate SYS

# Test result reads (write path is via the analysis engine)
PYTHONPATH=src:DHF python -m utils test list
PYTHONPATH=src:DHF python -m utils test list --status FAIL
PYTHONPATH=src:DHF python -m utils test status TC-SYS-001-001
```

## What Lives Outside DHF

| Concern | Location | Reason |
|---------|----------|--------|
| Compliance policies | `governance/` (repo root) | Core-system concern, not project data |
| Analysis engine | `src/compliantflow/` | Separate package; DHF-agnostic |
| Test framework adapter | `tests/conftest.py` | pytest-specific; not part of DHF |
| Virtual environment | `.venv/` (repo root) | Standard Python convention |

The `DHF/utils/` package has no dependency on `src/compliantflow/`. It can be used standalone or replaced by any backend that implements the `DHFAdapter` protocol.
