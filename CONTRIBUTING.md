# Contributing to MedHarness

MedHarness uses MedHarness itself to manage its own development — a
Change Request (CR) workflow that mirrors the design-controlled process the
tool enables for medical device teams. The table below describes how project
maintainers use the CR lifecycle; external contributors can open a standard
GitHub issue or PR directly.

## Development Setup

```bash
git clone https://github.com/itercharles/MedHarness
cd MedHarness
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ dhfkit/tests/ -q --ignore=dhfkit/tests/test_cli_doc_export.py
```

`pip install -e ".[dev]"` installs `medharness` from this repo with test dependencies.
No separate clone or install is needed.

## PR Conventions

- Branch naming: `feature/`, `fix/`, `refactor/`
- PR title must include the CR ID: `feat(CR-042): description`
- Body: change summary, DHF files updated, validation run, manual testing remaining

### PR Type Labels

Maintainers apply one of these labels before merging:

| Label | Version impact | When to use |
|-------|---------------|-------------|
| `breaking` | MAJOR | CLI, templates, scaffold output, or public API changes |
| `feature` | MINOR | New backward-compatible capability |
| `fix` | PATCH | Bug fixes, doc corrections |
| `internal` | None | Refactoring, test improvements, no user-visible change |

## When to Write a Design Doc

An ADR (using [docs/adr/ADR_TEMPLATE.md](docs/adr/ADR_TEMPLATE.md)) is required when:

- Adding or removing a CLI subcommand
- Modifying the scaffold output structure
- Modifying template directories or template variable contracts
- Modifying `dhfkit`'s public import API
- Modifying config schema compatibility
- Modifying release artifact structure
- Changing the role or usage patterns of the reference example project

Bug fixes, doc corrections, and pure internal refactoring do not require a design
doc but still require test coverage.

## Before Submitting

```bash
.venv/bin/pytest tests/unit/ tests/integration/ tests/contract/ dhfkit/tests/ -q --ignore=dhfkit/tests/test_cli_doc_export.py
.venv/bin/python -c "
from medharness.workflows.init import _scaffold_dhf
from pathlib import Path
import tempfile, subprocess, sys
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / 'd'
    _scaffold_dhf(d)
    subprocess.run([sys.executable, '-m', 'medharness', '--dhf', str(d/'DHF'), 'dhf', 'validate', 'schema'], check=True)
"
```
