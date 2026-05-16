# CLAUDE.md

## Project

MedHarness — open-source tooling for design-controlled development.
Includes `dhfkit`, the DHF/document/traceability engine.

## Guiding Documents

Before proposing or implementing any significant change, read:

- [`docs/architecture.md`](docs/architecture.md) — package boundaries, CR workflow
  topology, layer responsibilities, and test organisation. Do not violate the
  `dhfkit` → `medharness` import boundary.
- [`docs/roadmap.md`](docs/roadmap.md) — current project priorities and scope.
  Propose work that aligns with the active themes; call out explicitly if a
  proposed change falls outside scope.

## Repo Responsibility

| Directory | Purpose |
|-----------|---------|
| `medharness/` | Harness CLI, CI gate logic, scaffolding templates |
| `dhfkit/` | DHF engine: items, config, traceability, document generation |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, 12 sample items |
| `docs/` | Architecture and roadmap |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
| `tests/contract/` | Contract tests |
| `dhfkit/tests/` | dhfkit tests |

## Key Rules

- Product-formal docs are canonical in generated DHF repos, not here
- `dhfkit` has no dependency on `medharness` — the engine can be used standalone
- `ci test-coverage` enforces requirement-to-test coverage in consumer repos
- `ci evidence bundle` produces runtime evidence on merge to `main`
- All new `ci` commands must: output structured JSON to stdout, write
  human-readable summaries to stderr only, and exit non-zero on failure
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
