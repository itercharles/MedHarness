# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CompliantFlow is a Docs-as-Code ALM platform for medical devices. It manages Design History File (DHF) items — requirements, risks, tests, change requests — stored as YAML files under `DHF/items/`. The Streamlit UI (`src/app.py`) provides a web interface over a Python backend.

## Commands

### Run the application
```bash
streamlit run src/app.py
```

### CLI (CI/CD integration)
```bash
# Entry point: python -m compliantflow [--dhf PATH]
PYTHONPATH=src python -m compliantflow --help

# Common commands
PYTHONPATH=src python -m compliantflow validate schema
PYTHONPATH=src python -m compliantflow validate traceability
PYTHONPATH=src python -m compliantflow validate compliance IEC_62304
PYTHONPATH=src python -m compliantflow item list --type SYS --status approved
PYTHONPATH=src python -m compliantflow item get SYS-001
PYTHONPATH=src python -m compliantflow cr check-status CR-012
PYTHONPATH=src python -m compliantflow cr update CR-012 --item SYS-001 --pr-number 42
PYTHONPATH=src python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=src python -m compliantflow traceability chain SYS-001
# Test result integration (external CI → DHF)
PYTHONPATH=src python -m compliantflow test import results.xml --format junit --tester "GitHub Actions" --run-id 123 --run-url https://github.com/org/repo/actions/runs/123 --commit abc123
PYTHONPATH=src python -m compliantflow test status TC-SYS-001
PYTHONPATH=src python -m compliantflow test list --status PASS
```

CLI package is at `src/cli/cli.py`. Uses `click` (already installed via streamlit).
stdout = machine-readable JSON; stderr = human-readable messages.

### Run tests
```bash
# SYS tests (fast, recommended)
PYTHONPATH=src src/venv/bin/pytest tests/sys/ -v

# Single test
PYTHONPATH=$(pwd) src/venv/bin/pytest tests/sys/test_sys_001_object_management.py::test_name -v

# All unit tests (srs)
PYTHONPATH=$(pwd) src/venv/bin/pytest tests/srs/ -v
```

**Important**: Run from the repo root. Use `PYTHONPATH=src` for SYS/CRS tests; CI uses `PYTHONPATH="${PWD}/src"` for SRS tests.

## Architecture

### Core Facade: `CompliantFlowCore`
**`src/compliantflow/core.py`** is the single entry point for all business logic. Pages and tests interact only through this class. Import as `from compliantflow.core import CompliantFlowCore`.

The class is composed of seven mixins under `src/compliantflow/mixins/`:
- `lifecycle.py` — delegates to `traceability/lifecycle_methods.py`
- `item_crud.py` — `get_all_items`, `get_items_filtered`, `get_item`, `create/update/delete_item`
- `traceability.py` — `get_vertical_view_items`, `build_traceability_chains`, `build_traceability_matrix`, `get_item_chain`
- `change_request.py` — `get_cr_for_item`, `get_non_stable_cr`, `add_item_to_cr`, `can_edit_item`
- `schema_form.py` — `get_form_schema`, `get_relationship_options`, `get_doc_type_metrics`
- `compliance.py` — `get_policy_group`, `check_compliance`
- `test_results_mixin.py` — `import_test_results`, `get_test_result`, `get_all_test_results`

Key public methods:
- `get_all_items()` → `List[Dict]` — returns YAML items + TC items from ResultStore
- `get_items_filtered(doc_type_code, status_filter, search)` → filtered subset
- `get_item(uid)` → `Optional[Dict]`
- `create_item(data)`, `update_item(uid, data)`, `delete_item(uid)`
- `get_vertical_view_items(focus_type, show_upstream, show_downstream)`
- `build_traceability_chains(path)` → chain list for matrix rendering
- `check_compliance(group_id)` → compliance results with `policy_text` included
- `get_available_transitions(item)`, `execute_transition(item_id, to_state, performed_by)`
- `get_cr_for_item(item_id)`, `get_non_stable_cr()`, `add_item_to_cr(cr_id, item_id)`
- `build_traceability_matrix(doc_types)` → `{columns: [...], rows: [{DOC_TYPE: id|null, is_orphan, orphan_type, is_complete}]}`
- `get_item_chain(item_id)` → `{root: id, nodes: {id: {id, title, status, doc_type, upstream: [...], downstream: [...]}}}`
- `import_test_results(results, tester, run_id, run_url, commit_sha)` → `{imported, skipped, items_updated, failed_tcs}`
- `get_test_result(tc_id)` → `Optional[Dict]`
- `get_all_test_results(status_filter)` → `Dict[tc_id, record]`

**`get_all_items()` returns dicts, not `Item` objects.** Access fields with `item['id']`, `item.get('status')`, etc. The dict includes a computed `all_linked_uids` list for graph traversal — use this, not `item.get('links')` (which doesn't exist).

### Data Layer
- **`src/traceability/repository/loader.py`** — loads YAML, runs strict schema validation against doc-type properties from `project_config.yaml`. When `project_config` is provided to `ItemLoader`, unknown fields raise `ValidationError`.
- **`src/traceability/repository/saver.py`** — writes YAML and commits to git.
- Items are stored under `DHF/items/<directory>/`.

### Graph Engine
**`src/traceability/graph/engine.py`** builds a NetworkX `DiGraph`. **Edge direction is child→parent** (e.g., SRS-001 → SYS-001 for a `derives_from` link). This means:
- `nx.descendants(G, item_id)` = business-**upstream** (parents, grandparents)
- `nx.ancestors(G, item_id)` = business-**downstream** (children, grandchildren)

`get_item_chain(item_id)` traverses the full connected subgraph and returns correctly-named `upstream`/`downstream` keys per node.

### Config-Driven Document Types
**`DHF/config/project_config.yaml`** is the single source of truth. It defines:
- `doc_types[]`: each with `code`, `prefix`, `directory`, `properties[]`, `lifecycle`, `has_verification`
- `global_lifecycle.states[]`: all workflow states with `is_stable` flag
- `traceability_matrices[]`: ordered `path[]` of doc type codes for chain views

`ProjectConfig` and `DocTypeConfig` Pydantic models are in `src/traceability/models/config.py`.

### Schema Validation
`loader.py` validates each YAML against its doc type's `properties` list. Allowed fields per item = `_SYSTEM_FIELDS` (saver-written metadata: `id`, `doc_type`, `status`, `history`, etc., plus `reviewer`/`review_date` as core Item model fields) + fields declared in `properties` + lifecycle-derived fields (auto-computed from the doc type's `lifecycle` config: `{to_state}_by`/`{to_state}_date` for each transition, `manual_verifications` when manual criteria exist, `verification_status` when `has_verification: true`).

### Lifecycle / Transitions
- **`src/traceability/lifecycle_methods.py`** — `execute_transition()` only writes `status`. Audit fields (`approved_by`, `approved_date`, `reviewer`, `review_date`) are written by the UI layer before calling the transition.
- A state with `is_stable: true` locks the item — `is_item_editable()` returns `False`.

### External Test Result Integration

#### Architecture: framework-agnostic boundary

The system is deliberately split into two layers with a clean boundary:

```
tests/          ← framework-specific adapter (owned by the test project)
    conftest.py         pytest autouse fixture: reads docstring @-tags,
    utils/              calls record_property() → JUnit XML <properties>
        docstring_parser.py   shared helpers for tag extraction

────────────────── boundary: JUnit XML file ──────────────────

src/            ← framework-agnostic core (owned by CompliantFlow)
    test_results/
        junit_parser.py       reads compliantflow.* <property> elements
        result_store.py       persists to DHF/test-results/results.yaml
```

`src/` has no knowledge of pytest, docstrings, or any specific test framework.
It only consumes JUnit XML, which is a de-facto standard produced by virtually
every test framework (pytest, Jest, JUnit, Go testsum, RSpec, Mocha, …).

A team using a different framework provides their own adapter in their `tests/`
directory — a custom reporter, annotation processor, or wrapper — that writes
the same `compliantflow.*` properties into their JUnit XML output.

#### JUnit XML contract

The only interface between test code and CompliantFlow is the JUnit XML file:

```xml
<testcase name="test_TC_SYS_001_001_my_test">
  <properties>
    <property name="compliantflow.id"            value="TC-SYS-001-001"/>
    <property name="compliantflow.title"         value="My test title"/>
    <property name="compliantflow.links"         value="SYS-001, SYS-002"/>
    <property name="compliantflow.reviewer"      value="Alice"/>
    <property name="compliantflow.review_status" value="approved"/>
    <property name="compliantflow.review_date"   value="2026-01-15"/>
  </properties>
</testcase>
```

`compliantflow.id` falls back to regex extraction from the test name
(`test_TC_SYS_001_001_*` → `TC-SYS-001-001`) if the property is absent.
All other properties are optional. Tests with no recognisable TC ID are skipped.

#### pytest adapter (this project)

`tests/conftest.py` provides the pytest-specific adapter via an autouse fixture.
It reads `@`-tags from test docstrings and calls `record_property()` automatically
— no manual calls needed in individual tests.

Docstring format:
```python
def test_TC_SYS_001_001_my_test(test_dhf_root):
    """
    TC-SYS-001-001: My test title

    @test_id: TC-SYS-001-001   # optional if inferrable from function name
    @links: SYS-001             # required for traceability
    @reviewer: Alice            # optional; design-review metadata
    @review_status: approved    # optional
    @review_date: 2026-01-15    # optional
    """
```

Tag extraction helpers live in `tests/utils/docstring_parser.py`.

#### Storage

TC items have **no YAML files** and **no doc type definition** in `project_config.yaml`.
They live exclusively in `DHF/test-results/results.yaml` managed by `ResultStore`.
TC type is inferred from which requirements the TC links to.

After `test import`, `verification_status` is recomputed for each linked requirement
item: `verified` (all TCs PASS), `failed` (any TC FAIL), `not_verified` (no results).
Git history serves as the audit trail.

### CLI Layer
**`src/cli/cli.py`** exposes `CompliantFlowCore` as a `click` CLI. Sits alongside `debug_view/` as an interface layer, separate from the core package. Both entry points work:
- `python -m cli` — primary entry point
- `python -m compliantflow` — preserved for backward compatibility (delegates to `cli`)

### DebugView (internal Streamlit pages)
`src/debug_view/` contains Streamlit pages for internal development and debugging — **not a production UI**. Loaded explicitly via `st.Page(absolute_path)` in `app.py`.
- **`universal_page_template.py`** — renders the CRUD page for any doc type
- **`02_Traceability.py`** — traceability matrix and graph views
- **`03_Compliance.py`** — compliance policy assessment
- **`page_generator.py`** — generates page functions from `project_config.yaml`

## Testing Conventions

- All new tests go in `tests/sys/` as API-based tests (no browser/Playwright).
- Use the `test_dhf_root` fixture from `tests/sys/conftest.py` — it creates a fresh isolated DHF for each test.
- Test DHF config and items are defined in `tests/fixtures/test_data.py`.
- Test IDs follow `TC-SYS-NNN-NNN` pattern. Always include `@test_id:` and `@links:` docstring tags; add `@reviewer:`, `@review_status:`, `@review_date:` when the test has been design-reviewed.
- The autouse fixture in `tests/conftest.py` (the pytest adapter) automatically injects all docstring tags as `compliantflow.*` properties into JUnit XML — no manual `record_property` calls needed. Tag extraction logic lives in `tests/utils/docstring_parser.py`.
- `pytest.ini` sets `junit_family = xunit1` to enable per-testcase `<properties>`.
- Prefer `pytest.raises(ValidationError)` and similar assertions; avoid asserting exact error strings beyond key terms.

## PR Workflow

- Merge PRs with: `gh pr merge N --squash --delete-branch`
- Branch naming: `feature/`, `fix/`, `refactor/`
