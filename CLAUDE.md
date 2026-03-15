# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CompliantFlow is a Docs-as-Code ALM platform for medical devices. It manages Design History File (DHF) items — requirements, risks, tests, change requests — stored as YAML files under `DHF/items/`. The Python backend exposes a CLI for CI/CD integration and a library API for tests.

## Commands

### CLI (CI/CD integration)

Two separate CLIs:

```bash
# compliantflow CLI — read-only analysis (compliantflow/cli.py)
PYTHONPATH=.:DHF python -m compliantflow --help
PYTHONPATH=.:DHF python -m compliantflow validate traceability
PYTHONPATH=.:DHF python -m compliantflow validate compliance IEC_62304
PYTHONPATH=.:DHF python -m compliantflow validate compliance IEC_62304 --governance-dir governance
PYTHONPATH=.:DHF python -m compliantflow cr check-status CR-012
PYTHONPATH=.:DHF python -m compliantflow cr update CR-012 --item SYS-001
PYTHONPATH=.:DHF python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=.:DHF python -m compliantflow traceability chain SYS-001
# Test result integration (external CI → DHF)
PYTHONPATH=.:DHF python -m compliantflow test import results.xml --format junit --tester "GitHub Actions" --run-id 123 --run-url https://github.com/org/repo/actions/runs/123 --commit abc123
PYTHONPATH=.:DHF python -m compliantflow test status TC-SYS-001
PYTHONPATH=.:DHF python -m compliantflow test list --status PASS

# utils CLI (DHF data layer) — data CRUD, lifecycle, schema validation, doc generation (DHF/utils/cli.py)
PYTHONPATH=.:DHF python -m utils --help
PYTHONPATH=.:DHF python -m utils validate schema
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item get SYS-001
PYTHONPATH=.:DHF python -m utils item create --type SYS --data '{"title": "My req", "category": "Functional", "verification_method": ["Test"]}'
PYTHONPATH=.:DHF python -m utils item update SYS-001 --data '{"title": "Updated title"}'
PYTHONPATH=.:DHF python -m utils item delete SYS-001
PYTHONPATH=.:DHF python -m utils item transitions CR-012     # list available lifecycle transitions
PYTHONPATH=.:DHF python -m utils item transition CR-012 approved --by "Alice"  # execute transition
PYTHONPATH=.:DHF python -m utils doc list
PYTHONPATH=.:DHF python -m utils doc generate SYS
PYTHONPATH=.:DHF python -m utils doc generate ALL
PYTHONPATH=.:DHF python -m utils doc export SYS            # regenerate md then export PDF
PYTHONPATH=.:DHF python -m utils doc export ALL
```

stdout = machine-readable JSON; stderr = human-readable messages.

### Run tests
```bash
# Product tests — MUST run all before merging
PYTHONPATH=.:DHF .venv/bin/pytest tests/sys/ tests/crs/ -q

# DHF utility tests (independent; test the DHF data layer)
PYTHONPATH=.:DHF .venv/bin/pytest DHF/utils/tests/ -q

# Single test
PYTHONPATH=.:DHF .venv/bin/pytest tests/sys/test_sys_002_schema_validation.py::test_name -v
```

**Important**: Run from the repo root. Use `PYTHONPATH=.:DHF` for all CLI commands. Tests can also run without it (pytest.ini sets `pythonpath = . DHF`). **Before any merge, all product test suites (sys, crs) must pass.**

## Architecture

### Core Facade: `CompliantFlowCore`
**`compliantflow/core.py`** is the single entry point for all business logic. Tests interact only through this class. Import as `from compliantflow.core import CompliantFlowCore`.

**CompliantFlowCore is a read-only analysis facade.** All data mutations (create/update/delete items, execute lifecycle transitions) go through the DHFAdapter (and the `utils` CLI) directly. There are no mixins — all methods are defined directly in `core.py`.

Key public methods:
- `refresh()` — reload all items, rebuild graph, recompute verification status
- `get_config()` → `Optional[Dict]`
- `get_all_items()` → `List[Dict]` — returns YAML items + TC items from ResultStore
- `get_item(uid)` → `Optional[Dict]`
- `build_traceability_chains(path)` → chain list for matrix rendering
- `build_traceability_matrix(doc_types)` → `{columns: [...], rows: [{DOC_TYPE: id|null, is_orphan, orphan_type, is_complete}]}`
- `get_item_chain(item_id)` → `{root: id, nodes: {id: {id, title, status, type, upstream: [...], downstream: [...]}}}`
- `validate()` → graph validation result
- `get_policy_group(group_id, governance_dir)` → policy group dict (no checks run)
- `check_compliance(group_id, governance_dir)` → `{score, total_policies, passed_policies, results[{policy_id, passed, details, evidence, policy_text}]}`
- `import_test_results(results, tester, run_id, run_url, commit_sha)` → `{imported, skipped, items_updated, failed_tcs}`
- `get_test_result(tc_id)` → `Optional[Dict]`
- `get_all_test_results(status_filter)` → `Dict[tc_id, record]`

**`get_all_items()` returns dicts, not `Item` objects.** Access fields with `item['id']`, `item.get('status')`, etc. The dict includes a computed `all_linked_uids` list for graph traversal — use this, not `item.get('links')` (which doesn't exist).

### Data Layer
- **`DHF/utils/repository/loader.py`** — loads YAML, runs strict schema validation against doc-type properties. Unknown fields raise `ValidationError`.
- **`DHF/utils/repository/saver.py`** — writes YAML and commits to git.
- **`DHF/utils/local_adapter.py`** — `LocalDHFAdapter` wraps the utils package; `CompliantFlowCore` uses it via the `DHFAdapter` protocol (`compliantflow/adapters/protocol.py`).
- Items are stored under `DHF/items/<directory>/`.
- Documents are stored under `DHF/documents/` (any subdirectory). Access via logical ID (filename stem): `adapter.get_document("development_plan")` finds `documents/plans/development_plan.md`. `adapter.list_documents()` returns all stems.
- **`DHF/utils/lifecycle.py`** — standalone lifecycle engine (`get_available_transitions`, `execute_transition`). Used by `utils` CLI; CompliantFlowCore does **not** expose lifecycle mutation methods.

### Graph Engine
**`compliantflow/traceability/graph/engine.py`** builds a NetworkX `DiGraph`. **Edge direction is child→parent** (e.g., SRS-001 → SYS-001 for a `derives_from` link). This means:
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
- **`DHF/utils/lifecycle.py`** — standalone lifecycle engine: `get_available_transitions(item_id)`, `execute_transition(item_id, to_state, performed_by)`. Called from the `utils` CLI (`python -m utils item transitions <id>`, `python -m utils item transition <id> <state> --by <name>`).
- A state with `is_stable: true` locks the item.
- Lifecycle engine is a no-op for items whose doc type has no `lifecycle` config (requirement items).

### Compliance / PolicyEngine
**`compliantflow/policy.py`** — `PolicyEngine` executes automated policy checks against the graph. Instantiated internally by `core.check_compliance()`.

Eight built-in check types (`policy.automation.check` field in governance YAML):
| Check | Parameters | What it verifies |
|---|---|---|
| `item_existence` | `type_code` | Items of that type exist |
| `file_existence` | `path` | File exists relative to DHF root |
| `document_content` | `doc_id`, `keywords` | Document contains all keywords (case-insensitive) |
| `trace_coverage` | `source_type`, `target_type`, `min_coverage` | Source items link to target items |
| `attribute_presence` | `type_code`, `attribute` | All items have that attribute set |
| `attribute_value` | `type_code`, `attribute`, `expected_value` | All items have attribute == expected_value |
| `all_tests_passing` | `type_code` | All TC items linked to type items have PASS status |
| `verification_complete` | `type_code` | All items have `verification_status == 'verified'` |

Governance YAML lives under `governance/` (separate from DHF). Pass `governance_dir` explicitly: `core.check_compliance("IEC_62304", Path("governance"))`.

`IEC_62304.yaml` has 75/106 policies automated; 31 manual (QMS, procedural, organizational).

### External Test Result Integration

#### Architecture: framework-agnostic boundary

The system is deliberately split into two layers with a clean boundary:

```
tests/          ← framework-specific adapter (owned by the test project)
    conftest.py         pytest autouse fixture: reads docstring @-tags,
    utils/              calls record_property() → JUnit XML <properties>
        docstring_parser.py   shared helpers for tag extraction

────────────────── boundary: JUnit XML file ──────────────────

compliantflow/  ← framework-agnostic core (owned by CompliantFlow)
    test_results/
        junit_parser.py       reads compliantflow.* <property> elements
        result_store.py       persists to DHF/test-results/results.yaml
```

`compliantflow/` has no knowledge of pytest, docstrings, or any specific test framework.
It only consumes JUnit XML, which is a de-facto standard produced by virtually
every test framework (pytest, Jest, JUnit, Go testsum, RSpec, Mocha, …).

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
- **`compliantflow/cli.py`** — **read-only** analysis CLI (`python -m compliantflow`): traceability, compliance checks, CR status, test result import. No item mutations.
- **`DHF/utils/cli.py`** — data CLI (`python -m utils`): item CRUD, schema validation, lifecycle transitions, doc generation/export

## Testing Conventions

- All new tests go in `tests/sys/` as API-based tests.
- Use the `test_dhf_root` fixture from `tests/sys/conftest.py` — it creates a fresh isolated DHF for each test.
- Test DHF config and items are defined in `tests/fixtures/test_data.py`.
- Test IDs follow `TC-SYS-NNN-NNN` pattern. Always include `@test_id:` and `@links:` docstring tags; add `@reviewer:`, `@review_status:`, `@review_date:` when the test has been design-reviewed.
- The autouse fixture in `tests/conftest.py` (the pytest adapter) automatically injects all docstring tags as `compliantflow.*` properties into JUnit XML — no manual `record_property` calls needed. Tag extraction logic lives in `tests/utils/docstring_parser.py`.
- `pytest.ini` sets `junit_family = xunit1` to enable per-testcase `<properties>`.
- Prefer `pytest.raises(ValidationError)` and similar assertions; avoid asserting exact error strings beyond key terms.

## PR Workflow

- Merge PRs with: `gh pr merge N --squash --delete-branch`
- Branch naming: `feature/`, `fix/`, `refactor/`
