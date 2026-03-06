# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CompliantFlow is a Docs-as-Code ALM platform for medical devices. It manages Design History File (DHF) items — requirements, risks, tests, change requests — stored as YAML files under `DHF/items/`. The Streamlit UI (`src/debug_view/app.py`) provides a web interface over a Python backend.

## Commands

### Run the application
```bash
streamlit run src/debug_view/app.py
```

### CLI (CI/CD integration)

Two separate CLIs after the DHF data layer split (CR-013):

```bash
# compliantflow CLI — analysis, lifecycle, traceability (src/compliantflow/cli.py)
PYTHONPATH=src:DHF python -m compliantflow --help
PYTHONPATH=src:DHF python -m compliantflow validate traceability
PYTHONPATH=src:DHF python -m compliantflow validate compliance IEC_62304
PYTHONPATH=src:DHF python -m compliantflow item transitions SYS-001
PYTHONPATH=src:DHF python -m compliantflow item transition SYS-001 approved --by "Alice"
PYTHONPATH=src:DHF python -m compliantflow cr check-status CR-012
PYTHONPATH=src:DHF python -m compliantflow cr update CR-012 --item SYS-001 --pr-number 42
PYTHONPATH=src:DHF python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=src:DHF python -m compliantflow traceability chain SYS-001
# Test result integration (external CI → DHF)
PYTHONPATH=src:DHF python -m compliantflow test import results.xml --format junit --tester "GitHub Actions" --run-id 123 --run-url https://github.com/org/repo/actions/runs/123 --commit abc123
PYTHONPATH=src:DHF python -m compliantflow test status TC-SYS-001
PYTHONPATH=src:DHF python -m compliantflow test list --status PASS

# utils CLI (DHF data layer) — data CRUD, schema validation, doc generation (DHF/utils/cli.py)
PYTHONPATH=src:DHF python -m utils --help
PYTHONPATH=src:DHF python -m utils validate schema
PYTHONPATH=src:DHF python -m utils item list --type SYS
PYTHONPATH=src:DHF python -m utils item get SYS-001
PYTHONPATH=src:DHF python -m utils item create --type SYS --data '{"title": "My req", "category": "Functional", "verification_method": ["Test"]}'
PYTHONPATH=src:DHF python -m utils item update SYS-001 --data '{"title": "Updated title"}'
PYTHONPATH=src:DHF python -m utils item delete SYS-001
PYTHONPATH=src:DHF python -m utils doc list
PYTHONPATH=src:DHF python -m utils doc generate SYS
PYTHONPATH=src:DHF python -m utils doc generate ALL
PYTHONPATH=src:DHF python -m utils doc export SYS            # regenerate md then export PDF
PYTHONPATH=src:DHF python -m utils doc export ALL
```

stdout = machine-readable JSON; stderr = human-readable messages.

### Run tests
```bash
# Full suite — MUST run all three before merging
PYTHONPATH=src:DHF src/venv/bin/pytest tests/sys/ tests/crs/ -q
PYTHONPATH=src:DHF src/venv/bin/pytest tests/srs/ -q

# Single test
PYTHONPATH=src:DHF src/venv/bin/pytest tests/sys/test_sys_001_object_management.py::test_name -v
```

**Important**: Run from the repo root. Use `PYTHONPATH=src:DHF` for all test suites. **Before any merge, all three test suites (sys, crs, srs) must pass.**

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
- `document_generation_mixin.py` — `get_available_doc_types`, `generate_spec`

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
- `get_available_doc_types()` → `List[str]` — doc type codes with a `document_specifications` entry
- `generate_spec(doc_type_code)` → `{doc_type, output_path, version}` — writes markdown to DHF/documents/specifications/
- `get_test_result(tc_id)` → `Optional[Dict]`
- `get_all_test_results(status_filter)` → `Dict[tc_id, record]`

**`get_all_items()` returns dicts, not `Item` objects.** Access fields with `item['id']`, `item.get('status')`, etc. The dict includes a computed `all_linked_uids` list for graph traversal — use this, not `item.get('links')` (which doesn't exist).

### Data Layer
- **`DHF/utils/repository/loader.py`** — loads YAML, runs strict schema validation against doc-type properties. Unknown fields raise `ValidationError`.
- **`DHF/utils/repository/saver.py`** — writes YAML and commits to git.
- **`src/compliantflow/adapters/local.py`** — `LocalDHFAdapter` wraps the dhf package; `CompliantFlowCore` uses it via the `DHFAdapter` protocol (`src/compliantflow/adapters/protocol.py`).
- Items are stored under `DHF/items/<directory>/`.

### Graph Engine
**`src/traceability/graph/engine.py`** builds a NetworkX `DiGraph`. **Edge direction is child→parent** (e.g., SRS-001 → SYS-001 for a `derives_from` link). This means:
- `nx.descendants(G, item_id)` = business-**upstream** (parents, grandparents)
- `nx.ancestors(G, item_id)` = business-**downstream** (children, grandchildren)

`get_item_chain(item_id)` traverses the full connected subgraph and returns correctly-named `upstream`/`downstream` keys per node.

### Config-Driven Document Types
Config is split across two locations:
- **`DHF/config/global.yaml`** — global lifecycle states (`is_stable` flag), traceability matrices, document specifications
- **`DHF/config/doc_types/*.yaml`** — one file per doc type, each with `code`, `prefix`, `directory`, `properties[]`, `lifecycle` (optional), `has_verification`

`ProjectConfig` and `DocTypeConfig` Pydantic models are in `DHF/utils/models/config.py`. `ProjectConfig.load(config_dir)` reads the split format.

### GitOps Approval Model (requirement items)
**UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM** have **no `lifecycle` block** and **no `status` field**. Approval is implicit from Git:
- `main` branch = approved (merged via PR review)
- feature branch = draft / under review
- deleted from repo = retired

`get_initial_state()` returns `None` for these types; `get_available_transitions()` returns `[]`.

### Explicit Lifecycle (CR, REL, DEF only)
**CR, REL, DEF** retain explicit `lifecycle.transitions` in their doc type config with full state-machine workflows and criteria.

### Schema Validation
`loader.py` validates each YAML against its doc type's `properties` list. Allowed fields per item = `_SYSTEM_FIELDS` (saver-written metadata: `id`, `doc_type`, `status`, `history`, etc., plus `reviewer`/`review_date` as core Item model fields) + fields declared in `properties` + lifecycle-derived fields (auto-computed from the doc type's `lifecycle` config when present: `{to_state}_by`/`{to_state}_date` for each transition, `manual_verifications` when manual criteria exist, `verification_status` when `has_verification: true`).

### Lifecycle / Transitions
- **`src/traceability/lifecycle_methods.py`** — `execute_transition()` only writes `status`. Audit fields (`approved_by`, `approved_date`, `reviewer`, `review_date`) are written by the UI layer before calling the transition.
- A state with `is_stable: true` locks the item — `is_item_editable()` returns `False`.
- Lifecycle engine is a no-op for items whose doc type has no `lifecycle` config (requirement items).

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
Two CLI packages sit alongside `debug_view/` as interface layers, separate from the core packages:
- **`src/compliantflow/cli.py`** — analysis CLI (`python -m compliantflow`): traceability, compliance, lifecycle transitions, CR management, test result import
- **`DHF/utils/cli.py` — data CLI (`python -m utils`): item CRUD, schema validation, config inspection, doc generation/export

### DebugView (internal Streamlit pages)
`src/debug_view/` contains Streamlit pages for internal development and debugging — **not a production UI**. Loaded explicitly via `st.Page(absolute_path)` in `src/debug_view/app.py`.
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
