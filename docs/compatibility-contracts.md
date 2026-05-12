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
- CI enforces unit, integration, contract, and dhfkit test suites

### CLI Command Contracts

#### `medharness init`

- Generates the following core directories:
  - `DHF/config/` (with global.yaml and doc_types/)
  - `DHF/documents/specs/` (with .j2 templates)
  - `DHF/documents/plans/` (with plan documents)
  - `DHF/items/` (with subdirectories per doc type)
  - `DHF/test-results/`
- Writes product repo files: `CLAUDE.md`, `.gitignore`
- Substitutes: `{{project_name}}`, `{{product_repo}}`, `{{product_repo_name}}`, `{{github_org}}`, `{{dhf_repo_name}}`, `{{compliantflow_version}}`, `{{compliantflow_repo}}`, `{{primary_test_tool}}`

#### `medharness ci analyze-cr`

- Writes JSON to stdout with these keys:
  - `cr_id`
  - `stage`
  - `status`
  - `corrections`
  - `validation`
  - `errors`
  - `started_at`
  - `elapsed_ms`
  - `spec_path`
  - `spec_json_path`
  - `analysis`
- `analysis` contains these keys:
  - `direction_fit`
  - `affected_items`
  - `proposed_new_items`
  - `design_impact_summary`
  - `test_plan`
- Uses stderr only for human-readable summaries

#### `medharness ci cr-status`

- Writes JSON to stdout with these keys:
  - `cr_id`
  - `pr_number`
  - `branch_ref`
  - `stage`
  - `approval_label`
  - `approval_state`
  - `approved`
- `approval_state` is one of:
  - `approved`
  - `pending`
  - `not_applicable`
- Uses stderr only for human-readable summaries

#### `medharness ci validate-design`

- Writes JSON to stdout with these keys:
  - `cr_id`
  - `stage`
  - `passed`
  - `spec_path`
  - `errors`
- Uses exit code `0` when `passed` is true, non-zero otherwise

#### `medharness ci validate-code`

- Writes JSON to stdout with these keys:
  - `cr_id`
  - `stage`
  - `passed`
  - `spec_path`
  - `since_ref`
  - `errors`
- Uses exit code `0` when `passed` is true, non-zero otherwise

#### `medharness ci validate-branch`

- Writes JSON to stdout with these keys:
  - `cr_id`
  - `since_ref`
  - `passed`
  - `spec_path`
  - `expected_dhf_changes`
  - `spec_changes`
  - `dhf_item_changes`
  - `code_changes`
  - `errors`
- Requires the approved spec file to exist for the CR, but does not require
  that the implementation branch modify that spec file relative to `since_ref`
- Uses exit code `0` when `passed` is true, non-zero otherwise

#### `medharness ci github-event`

- Accepts GitHub event payloads from:
  - `workflow_dispatch`
  - `pull_request`
  - `pull_request_review`
  - `issue_comment`
  - `repository_dispatch`
- Writes JSON to stdout with these keys:
  - `cr_id`
  - `mode`
  - `pr_number`
  - `reason`
  - `event_name`
  - `branch_ref`
  - `review_state`
  - `merged`
  - `labels`
  - `dispatch_stage`
  - `stage`
  - `action`
- Uses caller-supplied mappings to decide `stage` and `action`; MedHarness
  parses event context but does not hardcode repo lifecycle policy

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

These variables are substituted by `medharness init`:

| Variable | Example value |
|----------|--------------|
| `{{project_name}}` | `Insulin Pump Firmware` |
| `{{product_repo}}` | `acme-medical/insulin-pump` |
| `{{product_repo_name}}` | `insulin-pump` |
| `{{github_org}}` | `acme-medical` |
| `{{dhf_repo_name}}` | `insulin-pump-dhf` |
| `{{compliantflow_version}}` | `0.3.5` |
| `{{compliantflow_repo}}` | `itercharles/MedHarness` |
| `{{primary_test_tool}}` | `pytest` |

### Template File Locations

- Templates are in `dhfkit/templates/specs/*.j2`
- CSS is in `dhfkit/templates/specs/styles/default.css`
- Plan templates are in `dhfkit/templates/plans/*.md`

---

## 4. Import API Contracts

Stable `dhfkit` imports:

```python
from dhfkit.models.item import Item
from dhfkit.models.config import ProjectConfig
from dhfkit.local_adapter import LocalDHFAdapter
from dhfkit.lifecycle import get_available_transitions, execute_transition
from dhfkit.traceability import check_traceability
from dhfkit.document_generation import DocumentGenerator
from dhfkit.change_requests import prepare_change_request, complete_change_request
from dhfkit.exceptions import ValidationError
from dhfkit.junit_parser import parse_junit_xml
from dhfkit.id_generator import get_next_id
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
    <property name="medharness.id" value="TC-SYS-027-001"/>
    <property name="medharness.links" value="SYS-027"/>
  </properties>
</testcase>
```

### `ci test-coverage`

Evaluates requirement-to-test coverage from JUnit evidence against a DHF repo.
This feature is available to scaffolded user repos. This repo uses layer-based
testing (unit, integration, contract) instead.

---

## 6. Non-Contracts (may change without MAJOR bump)

- Internal module layout within `medharness/` and `dhfkit/`
- Undocumented helper functions and classes
- Exact wording of starter sample items in templates/items/ (item count and structure are stable, content is not)
- Test utility code in `tests/`
- Sample automation wiring around the CLI
