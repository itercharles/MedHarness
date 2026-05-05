# Compatibility Contracts

> **Version:** 0.1.0
> **Last updated:** 2026-05-03

This document defines which behaviors are version-stable contracts and must
not change without a MAJOR version bump. See [CHANGELOG.md](../CHANGELOG.md)
for the versioning policy.

---

## 1. Tool-Repo Contracts (this repo's own stability)

### Test Organization

- Tests are organized by layer: `tests/unit/`, `tests/integration/`, `tests/contract/`
- Tests do not carry DHF requirement-linked metadata (`@links`, `@test_id`)
- CI enforces unit, integration, contract, and dhf_util test suites

### CLI Command Contracts

#### `compliantflow init`

- Generates the following core directories:
  - `DHF/config/` (with global.yaml and doc_types/)
  - `DHF/documents/specs/` (with .j2 templates)
  - `DHF/documents/plans/` (with plan documents)
  - `DHF/items/` (with subdirectories per doc type)
  - `DHF/test-results/`
  - `.github/workflows/`
- Writes product repo files: `CLAUDE.md`, `.github/workflows/engineering-control.yml`, `.github/workflows/cr-complete.yml`, `.github/workflows/review-pr.yml`, `.claude/skills/pre-analyze/`, `.claude/skills/cr-implement/`, `.claude/skills/traceability-check/`
- Writes DHF repo files: `AI-harness/context.md`
- Substitutes: `{{project_name}}`, `{{product_repo}}`, `{{product_repo_name}}`, `{{github_org}}`, `{{dhf_repo_name}}`, `{{compliantflow_version}}`, `{{compliantflow_repo}}`, `{{primary_test_tool}}`

### Output Format

- Automation commands (`item get`, `item list`, `item create`, `doc list`,
  `doc generate`, `test list`) write JSON to stdout and
  human-readable messages to stderr.
- `item get`, `item list` return JSON with at minimum: `id`, `title`, `type`, `all_linked_uids`
- Interactive validation commands (`validate schema`, `validate traceability`)
  write human-readable output to stderr; machine-readable exit codes indicate
  pass/fail.

---

## 2. Config Schema Contracts

### `DHF/config/global.yaml`

Required fields:
- `project_name` — project display name
- `global_lifecycle` — lifecycle states
- `traceability_matrices` — traceability paths
- `document_specifications` — per-doc-type template and output paths
- `test_integration` — result store configuration

### `DHF/config/doc_types/*.yaml`

Required fields:
- `code` — short type code (e.g., `SYS`)
- `prefix` — ID prefix (e.g., `SYS-`)
- `directory` — items subdirectory (e.g., `02_sys`)

Optional fields:
- `type_name` — display name
- `properties` — field definitions
- `lifecycle` — state machine transitions
- `has_verification` — whether items support verification status

---

## 3. Template Contracts

### Template Variables

These variables are substituted by `compliantflow init`:

| Variable | Example value |
|----------|--------------|
| `{{project_name}}` | `Insulin Pump Firmware` |
| `{{product_repo}}` | `acme-medical/insulin-pump` |
| `{{product_repo_name}}` | `insulin-pump` |
| `{{github_org}}` | `acme-medical` |
| `{{dhf_repo_name}}` | `insulin-pump-dhf` |
| `{{compliantflow_version}}` | `0.1.0` |
| `{{compliantflow_repo}}` | `itercharles/CompliantFlow` |
| `{{primary_test_tool}}` | `pytest` |

### Template File Locations

- Templates are in `dhf_util/templates/specs/*.j2`
- CSS is in `dhf_util/templates/specs/styles/default.css`
- Plan templates are in `dhf_util/templates/plans/*.md`

---

## 4. Import API Contracts

Stable `dhf_util` imports:

```python
from dhf_util.models.item import Item
from dhf_util.models.config import ProjectConfig
from dhf_util.local_adapter import LocalDHFAdapter
from dhf_util.lifecycle import get_available_transitions, execute_transition
from dhf_util.traceability import check_traceability
from dhf_util.document_generation import DocumentGenerator
from dhf_util.change_requests import prepare_change_request, complete_change_request
from dhf_util.exceptions import ValidationError
from dhf_util.junit_parser import parse_junit_xml
from dhf_util.id_generator import get_next_id
```

---

## 5. Scaffolded User-Repo Supported Behaviors

These features are supported for **generated user DHF repos**, not used for
this repo's own governance:

### JUnit Evidence Contract

Tests in user repos may emit JUnit XML with:
```xml
<testcase name="test_TC_SYS_027_001_...">
  <properties>
    <property name="compliantflow.id" value="TC-SYS-027-001"/>
    <property name="compliantflow.links" value="SYS-027"/>
  </properties>
</testcase>
```

### `ci test-coverage`

Evaluates requirement-to-test coverage from JUnit evidence against a DHF repo.
This feature is available to scaffolded user repos. This repo uses layer-based
testing (unit, integration, contract) instead.

---

## 6. Non-Contracts (may change without MAJOR bump)

- Internal module layout within `compliantflow/` and `dhf_util/`
- Undocumented helper functions and classes
- Exact wording of starter sample items in templates/items/ (item count and structure are stable, content is not)
- Test utility code in `tests/`
- CI workflow internals (as long as gate semantics are preserved)
