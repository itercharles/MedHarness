# CLAUDE.md

## Project

MedHarness — open-source tooling for design-controlled development.
Includes `dhfkit`, the DHF/document/traceability engine.

## Repo Responsibility

| Directory | Purpose |
|-----------|---------|
| `medharness/` | Harness CLI, CI gate logic, scaffolding templates |
| `dhfkit/` | DHF engine: items, config, traceability, document generation |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, 12 sample items |
| `docs/` | Architecture, design docs, compatibility contracts |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
| `tests/contract/` | Contract tests |
| `dhfkit/tests/` | dhfkit tests |

## Key Rules

- Product-formal docs are canonical in generated DHF repos, not here
- `ci test-coverage` enforces requirement-to-test coverage
- `ci evidence bundle` produces runtime evidence on merge to `main`
- `dhfkit` has no dependency on `medharness` — the engine can be used standalone
- Do not add comments to self-explanatory code. Only comment when the WHY is
  non-obvious: a hidden constraint, a workaround, an external API contract, or
  behavior that would surprise a reader unfamiliar with the context.

## Test Environment

The repo has a `.venv` at the root. `pytest.ini` sets `pythonpath = .` so no
`PYTHONPATH` prefix is needed.

```bash
.venv/bin/pytest dhfkit/tests/ tests/ -q --ignore=dhfkit/tests/test_cli_doc_export.py
```

`test_cli_doc_export.py` requires `libgobject` (WeasyPrint native lib) — skip it locally.
