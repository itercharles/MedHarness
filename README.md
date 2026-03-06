# CompliantFlow

CompliantFlow is a Docs-as-Code ALM (Application Lifecycle Management) platform for Medical Devices. It manages a Design History File (DHF) — requirements, risks, tests, change requests — stored as YAML files and tracked in Git.

## Repository Layout

```
CompliantFlow/
├── DHF/                        # Design History File (the data)
│   ├── items/                  # Requirement items (YAML, one file per item)
│   ├── config/                 # Project config (global.yaml + doc_types/)
│   ├── test-results/           # Automated test results (results.yaml)
│   ├── documents/              # Generated specification documents
│   └── utils/                  # DHF data-layer package (importable as `utils`)
│       ├── models/             # Pydantic models (Item, ProjectConfig, …)
│       ├── repository/         # ItemLoader, ItemSaver, GitRepository
│       ├── result_store.py     # Test result persistence
│       ├── junit_parser.py     # JUnit XML import (framework-agnostic)
│       └── cli.py              # DHF CLI entry point (python -m utils)
├── governance/                 # Compliance policy groups (IEC_62304.yaml, …)
├── src/                        # Python analysis engine
│   ├── compliantflow/          # Core analysis package
│   │   ├── core.py             # CompliantFlowCore facade
│   │   ├── cli.py              # Analysis CLI (python -m compliantflow)
│   │   ├── adapters/           # DHFAdapter protocol + LocalDHFAdapter
│   │   ├── mixins/             # Traceability, compliance, lifecycle, …
│   │   ├── traceability/       # Graph engine, lifecycle, compliance engine
│   │   └── helpers/            # UI helper utilities
│   └── debug_view/             # Streamlit debug UI (not production)
│       ├── app.py              # Streamlit entry point
│       ├── page_generator.py   # Dynamic page generation from config
│       └── universal_page_template.py
├── tests/                      # Test suites
│   ├── sys/                    # SYS-level API tests
│   ├── crs/                    # CRS-level scenario tests
│   └── srs/                    # SRS-level unit tests
├── requirements.txt
└── .venv/                      # Virtual environment (gitignored)
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

### Debug UI (Streamlit)
```bash
PYTHONPATH=src:DHF streamlit run src/debug_view/app.py
```

### Analysis CLI
```bash
# Traceability, compliance, lifecycle, change requests, test import
PYTHONPATH=src:DHF python -m compliantflow --help
PYTHONPATH=src:DHF python -m compliantflow validate traceability
PYTHONPATH=src:DHF python -m compliantflow validate compliance IEC_62304
PYTHONPATH=src:DHF python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=src:DHF python -m compliantflow test import results.xml --format junit --tester "CI"
```

### DHF Data CLI
```bash
# Item CRUD, schema validation, document generation, test result reads
PYTHONPATH=src:DHF python -m utils --help
PYTHONPATH=src:DHF python -m utils item list --type SYS
PYTHONPATH=src:DHF python -m utils item create --type SYS --data '{"title": "My req"}'
PYTHONPATH=src:DHF python -m utils validate schema
PYTHONPATH=src:DHF python -m utils doc generate ALL
PYTHONPATH=src:DHF python -m utils test list --status FAIL
```

## Testing

```bash
# All three suites must pass before merging
PYTHONPATH=src:DHF .venv/bin/pytest tests/sys/ tests/crs/ -q
PYTHONPATH=src:DHF .venv/bin/pytest tests/srs/ -q
```

## Architecture

CompliantFlow is split into two independent layers:

| Layer | Package | Purpose |
|---|---|---|
| DHF data layer | `DHF/utils/` | YAML CRUD, schema, doc generation, test result storage |
| Analysis engine | `src/compliantflow/` | Graph, traceability, compliance, lifecycle |

The analysis engine connects to the data layer via the `DHFAdapter` protocol (`src/compliantflow/adapters/protocol.py`). The default implementation is `LocalDHFAdapter` which wraps `DHF/utils/`. Alternative backends (cloud, database) can plug in by implementing the same protocol.

**GitOps approval model**: Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM) have no `status` field. Approval is implicit from Git: `main` branch = approved, feature branch = draft.

**Compliance**: Policy groups live in `governance/` at the repository root. The analysis engine reads them directly — governance is a core-system concern, not DHF data.
