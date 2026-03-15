# CompliantFlow

CompliantFlow is a Docs-as-Code ALM (Application Lifecycle Management) platform for Medical Devices. It manages a Design History File (DHF) — requirements, risks, tests, change requests — stored as YAML files and tracked in Git.

## Repository Layout

```
CompliantFlow/
├── DHF/                        # Design History File (the data)
│   ├── items/                  # Requirement items (YAML, one file per item)
│   ├── config/                 # Project config (global.yaml + doc_types/)
│   ├── test-results/           # Automated test results (results.yaml)
│   ├── documents/              # DHF documents (plans/, specifications/, …)
│   └── utils/                  # DHF data-layer package (importable as `utils`)
│       ├── models/             # Pydantic models (Item, ProjectConfig, …)
│       ├── repository/         # ItemLoader, ItemSaver, GitRepository
│       ├── lifecycle.py        # Standalone lifecycle engine
│       ├── result_store.py     # Test result persistence
│       ├── junit_parser.py     # JUnit XML import (framework-agnostic)
│       └── cli.py              # DHF CLI entry point (python -m utils)
├── governance/                 # Compliance policy groups (IEC_62304.yaml, …)
├── compliantflow/              # Read-only analysis engine package
│   ├── core.py                 # CompliantFlowCore facade (read-only)
│   ├── cli.py                  # Analysis CLI (python -m compliantflow)
│   ├── policy.py               # PolicyEngine (compliance checks)
│   ├── adapters/               # DHFAdapter protocol + LocalDHFAdapter
│   └── traceability/           # Graph engine
├── tests/                      # Test suites
│   ├── sys/                    # SYS-level API tests
│   ├── crs/                    # CRS-level scenario tests
│   └── fixtures/               # Shared test data and DHF setup
├── requirements.txt
└── .venv/                      # Virtual environment (gitignored)
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

### Analysis CLI (read-only)
```bash
# Traceability, compliance checks, CR status, test result import
PYTHONPATH=.:DHF python -m compliantflow --help
PYTHONPATH=.:DHF python -m compliantflow validate traceability
PYTHONPATH=.:DHF python -m compliantflow validate compliance IEC_62304
PYTHONPATH=.:DHF python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=.:DHF python -m compliantflow test import results.xml --format junit --tester "CI"
```

### DHF Data CLI
```bash
# Item CRUD, lifecycle transitions, schema validation, document generation
PYTHONPATH=.:DHF python -m utils --help
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item create --type SYS --data '{"title": "My req"}'
PYTHONPATH=.:DHF python -m utils item transitions CR-001
PYTHONPATH=.:DHF python -m utils item transition CR-001 approved --by "Alice"
PYTHONPATH=.:DHF python -m utils validate schema
PYTHONPATH=.:DHF python -m utils doc generate ALL
```

## Testing

```bash
# All suites must pass before merging
PYTHONPATH=.:DHF .venv/bin/pytest tests/sys/ tests/crs/ -q
```

## Architecture

CompliantFlow is split into two independent layers:

| Layer | Package | Purpose |
|---|---|---|
| DHF data layer | `DHF/utils/` | YAML CRUD, lifecycle, schema, doc generation, test result storage |
| Analysis engine | `compliantflow/` | Read-only: graph, traceability, compliance reporting |

The analysis engine connects to the data layer via the `DHFAdapter` protocol (`compliantflow/adapters/protocol.py`). The default implementation is `LocalDHFAdapter` which wraps `DHF/utils/`. Alternative backends (cloud, database) can plug in by implementing the same protocol.

**CompliantFlowCore is read-only.** All data mutations (create/update/delete items, lifecycle transitions) go through the DHFAdapter directly or via `python -m utils`.

**GitOps approval model**: Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM) have no `status` field. Approval is implicit from Git: `main` branch = approved, feature branch = draft.

**Compliance**: Policy groups live in `governance/` at the repository root. Pass `governance_dir` explicitly when running checks:
```python
core.check_compliance("IEC_62304", Path("governance"))
```
