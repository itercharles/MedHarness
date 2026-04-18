# DHF Utils — Internal Documentation

This directory contains requirements, architecture decisions, and design specifications
for the `DHF/utils/` data-layer package. These documents describe the internal
infrastructure of CompliantFlow, **not** the product itself.

> The product DHF (`DHF/items/`) documents what CompliantFlow does for users.
> This directory documents how `DHF/utils/` is built and why.

---

## Modules

| Module | File(s) | Description |
|--------|---------|-------------|
| **Item Management** | `repository/loader.py`, `repository/saver.py` | YAML I/O, schema validation, Git tracking |
| **Traceability Graph** | `(in src/compliantflow/traceability/)` | NetworkX DiGraph, orphan detection, coverage |
| **Configurable Workflow** | `(in src/compliantflow/traceability/lifecycle_methods.py)` | State machine for CR/REL/DEF only |
| **Compliance Validation** | `(in src/compliantflow/traceability/compliance/)` | Policy-based validation engine |
| **Document Generation** | `document_generation.py` | Jinja2 templates → Markdown → PDF (WeasyPrint) |
| **Test Result Integration** | `junit_parser.py`, `result_store.py` | JUnit XML parsing, result persistence |
| **Configuration Models** | `models/config.py` | `ProjectConfig`, `DocTypeConfig` Pydantic models |
| **GitOps Approval** | *(architectural decision)* | Requirement items: no status, approval via Git |
| **Component Boundary** | *(architectural decision)* | DHF / CompliantFlow / tests import rules |
| **GitHub Artifact Fetcher** | `artifact_fetcher.py` | On-demand test result retrieval from CI artifacts |

---

## Documents

- [`requirements.md`](requirements.md) — Functional requirements for each module
- [`architecture.md`](architecture.md) — Architectural decisions and module structure
- [`design.md`](design.md) — Software detailed design (algorithms, interfaces, patterns)

---

## Tests

Tests for this package live in `DHF/utils/tests/`. Run with:

```bash
PYTHONPATH=src:DHF .venv/bin/pytest DHF/utils/tests/ -q
```
