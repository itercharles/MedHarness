# CompliantFlow

CompliantFlow is a compliance checking tool for medical device software. It connects to a project's Design History File (DHF) via the `DHFAdapter` interface and verifies compliance against IEC 62304, ISO 14971, and IEC 82304-1 in CI.

CompliantFlow's own DHF lives in a separate repository: [compliantflow-dhf](https://github.com/itercharles/compliantflow-dhf). Clone it alongside this repo to run the CLI and compliance checks.

## Repository Layout

```
CompliantFlow/
├── compliantflow/              # Read-only analysis engine
│   ├── core.py                 # CompliantFlowCore facade
│   ├── cli.py                  # Analysis CLI (python -m compliantflow)
│   ├── policy.py               # PolicyEngine (compliance checks)
│   ├── adapters/               # DHFAdapter protocol
│   └── traceability/           # Graph engine
├── tests/                      # Test suites (use StubDHFAdapter, no DHF needed)
│   ├── sys/                    # SYS-level API tests
│   ├── crs/                    # CRS-level scenario tests
│   └── fixtures/               # Shared test data
├── requirements.txt
└── .venv/                      # Virtual environment (gitignored)
```

DHF data (`DHF/`) and governance policy files (`governance/`) live in [compliantflow-dhf](https://github.com/itercharles/compliantflow-dhf).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Clone the DHF alongside this repo
git clone https://github.com/itercharles/compliantflow-dhf
export PYTHONPATH=.:compliantflow-dhf/DHF
```

## Running

### Analysis CLI (read-only)
```bash
python -m compliantflow --dhf compliantflow-dhf/DHF validate traceability
python -m compliantflow --dhf compliantflow-dhf/DHF validate compliance IEC_62304 \
  --governance-dir compliantflow-dhf/governance
python -m compliantflow --dhf compliantflow-dhf/DHF traceability matrix CRS SYS SRS
python -m compliantflow --dhf compliantflow-dhf/DHF cr check-status CR-001
```

### DHF Data CLI (run from compliantflow-dhf/)
```bash
cd compliantflow-dhf
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item create --type SYS --data '{"title": "My req"}'
PYTHONPATH=.:DHF python -m utils item transition <CR-ID> approved --by "Alice"
PYTHONPATH=.:DHF python -m utils validate schema
```

## Testing

Tests use `StubDHFAdapter` (in-memory) and require no DHF checkout:

```bash
PYTHONPATH=. .venv/bin/pytest tests/sys/ tests/crs/ -q
```

## Architecture

CompliantFlow connects to any DHF via the `DHFAdapter` protocol (`compliantflow/adapters/protocol.py`). The tool has no knowledge of how the DHF stores data — it only depends on the interface.

| Layer | Location | Purpose |
|---|---|---|
| Analysis engine | `compliantflow/` (this repo) | Read-only: traceability, compliance, reporting |
| DHF data layer | `compliantflow-dhf/DHF/utils/` | YAML CRUD, lifecycle, schema, test result storage |

**CompliantFlowCore is read-only.** All data mutations go through `python -m utils` in the DHF repo.

**GitOps approval**: Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, RISK, RCM) are approved by landing on `main`. No explicit status field.

**Compliance**: Governance policy files live in `compliantflow-dhf/governance/`. Pass `--governance-dir` when running checks.
