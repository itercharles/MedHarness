# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CompliantFlow is a Docs-as-Code ALM platform for medical devices. It manages Design History File (DHF) items — requirements, risks, tests, change requests — stored as YAML files under `DHF/items/`. The Streamlit UI (`src/app.py`) provides a web interface over a Python backend.

## Commands

### Run the application
```bash
cd src
source venv/bin/activate
streamlit run app.py
```

### Run tests
```bash
# SYS tests (fast, recommended — ~3 seconds for all 59 tests)
PYTHONPATH=$(pwd) src/venv/bin/pytest tests/sys/ -v

# Single test
PYTHONPATH=$(pwd) src/venv/bin/pytest tests/sys/test_sys_001_object_management.py::test_name -v

# All unit tests (srs)
PYTHONPATH=$(pwd) src/venv/bin/pytest tests/srs/ -v
```

**Important**: Run from the repo root; `PYTHONPATH=$(pwd)` must point to the repo root (not `src/`). Tests use `sys.path.insert(0, ...)` to find `src/traceability/`.

### Validate items against schema
```bash
cd src && source venv/bin/activate
python validate_items.py ../DHF
```

## Architecture

### Core Facade: `CompliantFlowCore`
**`src/traceability/compliant_flow_core.py`** is the single entry point for all business logic. Pages and tests interact only through this class.

Key public methods:
- `get_all_items()` → `List[Dict]` — returns YAML items + auto-scanned tests from `tests/`
- `get_items_filtered(doc_type_code, status_filter, search)` → filtered subset
- `get_item(uid)` → `Optional[Dict]`
- `create_item(data)`, `update_item(uid, data)`, `delete_item(uid)`
- `get_item_neighbors(item_id)` → `{"upstream": [...], "downstream": [...]}`
- `get_vertical_view_items(focus_type, show_upstream, show_downstream)`
- `build_traceability_chains(path)` → chain list for matrix rendering
- `check_compliance(group_id)` → compliance results with `policy_text` included
- `get_available_transitions(item)`, `execute_transition(item_id, to_state, performed_by)`
- `get_cr_for_item(item_id)`, `get_non_stable_cr()`, `add_item_to_cr(cr_id, item_id)`

**`get_all_items()` returns dicts, not `Item` objects.** Access fields with `item['id']`, `item.get('status')`, etc. The dict includes a computed `all_linked_uids` list for graph traversal — use this, not `item.get('links')` (which doesn't exist).

### Data Layer
- **`src/traceability/repository/loader.py`** — loads YAML, runs strict schema validation against doc-type properties from `project_config.yaml`. When `project_config` is provided to `ItemLoader`, unknown fields raise `ValidationError`.
- **`src/traceability/repository/saver.py`** — writes YAML and commits to git.
- Items are stored under `DHF/items/<directory>/`.

### Graph Engine
**`src/traceability/graph/engine.py`** builds a NetworkX `DiGraph`. **Edge direction is child→parent** (e.g., SRS-001 → SYS-001 for a `derives_from` link). This means:
- `nx.descendants(G, item_id)` = business-**upstream** (parents, grandparents)
- `nx.ancestors(G, item_id)` = business-**downstream** (children, grandchildren)

`CompliantFlowCore.get_item_neighbors()` returns correctly-named `upstream`/`downstream` keys.

### Config-Driven Document Types
**`DHF/config/project_config.yaml`** is the single source of truth. It defines:
- `doc_types[]`: each with `code`, `prefix`, `directory`, `properties[]`, `lifecycle`, `has_verification`
- `global_lifecycle.states[]`: all workflow states with `is_stable` flag
- `traceability_matrices[]`: ordered `path[]` of doc type codes for chain views

`ProjectConfig` and `DocTypeConfig` Pydantic models are in `src/traceability/models/config.py`.

### Schema Validation
`loader.py` validates each YAML against its doc type's `properties` list. Allowed fields per item = `_SYSTEM_FIELDS` (saver-written metadata: `id`, `doc_type`, `status`, `history`, etc., plus `reviewer`/`review_date` as core Item model fields) + fields declared in `properties` + lifecycle-derived fields (auto-computed from the doc type's `lifecycle` config: `{to_state}_by`/`{to_state}_date` for each transition, `manual_verifications` when manual criteria exist, `verification_status` when `has_verification: true`). Use `src/validate_items.py DHF` to check the real DHF.

### Lifecycle / Transitions
- **`src/traceability/lifecycle_methods.py`** — `execute_transition()` only writes `status`. Audit fields (`approved_by`, `approved_date`, `reviewer`, `review_date`) are written by the UI layer before calling the transition.
- A state with `is_stable: true` locks the item — `is_item_editable()` returns `False`.

### Pages
- **`src/pages/universal_page_template.py`** — renders the CRUD page for any doc type; called by dynamically generated pages.
- **`src/pages/02_Traceability.py`** — traceability matrix and graph views.
- **`src/pages/03_Compliance.py`** — compliance policy assessment.
- **`src/pages/page_generator.py`** — generates Streamlit page files from `project_config.yaml`.

## Testing Conventions

- All new tests go in `tests/api/` as API tests (no browser/Selenium).
- Use the `test_dhf_root` fixture from `tests/api/conftest.py` — it creates a fresh isolated DHF for each test.
- Test DHF config and items are defined in `tests/fixtures/test_data.py`.
- Test IDs follow `TC-SYS-NNN-NNN` pattern. Add `@test_id:` and `@links:` docstring tags.
- Prefer `pytest.raises(ValidationError)` and similar assertions; avoid asserting exact error strings beyond key terms.

## PR Workflow

- Merge PRs with: `gh pr merge N --squash --delete-branch`
- Branch naming: `feature/`, `fix/`, `refactor/`
