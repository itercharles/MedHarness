# Agent Environment

CompliantFlow is a Docs-as-Code ALM platform for medical devices. It manages
Design History File (DHF) items — requirements, risks, tests, change requests —
stored as YAML files under `DHF/items/`. The Python backend exposes a CLI for
CI/CD integration and a library API for tests.

This document defines the stable operating context for any LLM or coding agent
working in this repository.

It answers:
- what parts of the repo are authoritative
- what environment assumptions hold
- what invariants matter before making changes
- what existing command surface agents should reuse

Workflow, validation order, PR/CR handling, and CI usage live in
[`docs/agent_workflow.md`](agent_workflow.md).

## Sources Of Truth

Use these repository surfaces according to what kind of truth you need:

1. [`README.md`](../README.md)
   - repository layout and setup
2. [`DHF/`](../DHF)
   - project facts, configuration, documents, item state, and verification evidence
3. [`governance/`](../governance)
   - compliance expectations and policy definitions
4. [`/.github/workflows/ci-pipeline.yml`](../.github/workflows/ci-pipeline.yml)
   - enforced acceptance path and merge gates
5. [`AGENTS.md`](../AGENTS.md) or [`CLAUDE.md`](../CLAUDE.md)
   - agent-specific entry guidance

Do not create a second command set, a second CI path, or a second architecture
document unless the repository workflow actually changes.

## Environment Contract

Work from the repository root. Use the established environment:

```bash
PYTHONPATH=.:DHF
```

Use the repository virtual environment:

```bash
.venv/
```

The environment has four practical layers:

1. `DHF/`
   - project data model, documents, and persisted test evidence
2. `compliantflow/`
   - read-only analysis, traceability, compliance, and reporting
3. `governance/`
   - policy groups evaluated by the compliance engine
4. local tests and GitHub Actions
   - validation and merge acceptance

## Key Repository Invariants

- `CompliantFlowCore` is read-only.
  - Use `python -m compliantflow` for analysis.
  - Use `python -m utils` for DHF mutations and lifecycle transitions.
- Graph edges are child to parent in `compliantflow/graph.py`.
  - `descendants()` means business-upstream.
  - `ancestors()` means business-downstream.
- Requirement items such as `UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`,
  `SOUP`, `RISK`, and `RCM` use GitOps approval.
  - `main` implies approved.
  - feature branches imply draft or in review.
- `CR`, `REL`, and `DEF` use explicit lifecycle transitions.
- `document_semantic` in `compliantflow/policy.py` is the main LLM-sensitive path.
  - It evaluates governance requirements against DHF documents using Gemini.
- External test integration crosses the repository boundary via JUnit XML.
  - test frameworks emit XML
  - `compliantflow` imports and persists the results
- `python -m utils item update ...` resets lifecycle state for `CR`, `REL`, and
  `DEF` items to their initial state.
  - update before transitions, or re-run transitions afterward

## CompliantFlowCore Public API

**`compliantflow/core.py`** is the single entry point for all business logic.
Import as `from compliantflow.core import CompliantFlowCore`.

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

**`get_all_items()` returns dicts, not `Item` objects.** Access fields with
`item['id']`, `item.get('status')`, etc. The dict includes a computed
`all_linked_uids` list for graph traversal — use this, not `item.get('links')`
(which doesn't exist).

## Config Structure

Config is split across two locations:

- **`DHF/config/global.yaml`** — global lifecycle states (`is_stable` flag),
  traceability matrices, document specifications
- **`DHF/config/doc_types/*.yaml`** — one file per doc type, each with `code`,
  `prefix`, `directory`, `properties[]`, `lifecycle` (optional), `has_verification`

`ProjectConfig` and `DocTypeConfig` Pydantic models are in
`DHF/utils/models/config.py`. `ProjectConfig.load(config_dir)` reads the split
format.

## Compliance / PolicyEngine

**`compliantflow/policy.py`** — `PolicyEngine` executes automated policy checks
against the graph. Instantiated internally by `core.check_compliance()`.

Ten built-in check types (`policy.automation.check` field in governance YAML):

| Check | Parameters | What it verifies |
|---|---|---|
| `item_existence` | `type_code` | Items of that type exist |
| `file_existence` | `path` | File exists relative to DHF root |
| `document_content` | `doc_id`, `keywords` | Document contains all keywords (case-insensitive) |
| `document_semantic` | `doc_id`, `requirement` | Gemini LLM checks document satisfies a requirement |
| `trace_coverage` | `source_type`, `target_type`, `min_coverage` | Source items link to target items |
| `attribute_presence` | `type_code`, `attribute` | All items have that attribute set |
| `attribute_value` | `type_code`, `attribute`, `expected_value` | All items have attribute == expected_value |
| `all_tests_passing` | `type_code` | All TC items linked to type items have PASS status |
| `verification_complete` | `type_code` | All items have `verification_status == 'verified'` |
| `cr_git_evidence` | *(reads `COMPLIANTFLOW_CR_REPORT_PATH` env var or `report_path` param)* | CR-PR report JSON has at least one commit |

Governance YAML lives under `governance/` (separate from DHF). Pass
`governance_dir` explicitly: `core.check_compliance("IEC_62304", Path("governance"))`.

Three standards are currently defined:
- `IEC_62304.yaml` — 75/106 policies automated; 31 manual (QMS, procedural, organizational)
- `IEC_82304_1.yaml` — health software product safety
- `ISO_14971.yaml` — risk management

## Test And Evidence Interfaces

- New API-facing product tests normally live under `tests/sys/`.
  - Use `tests/crs/` for CRS-level scenario coverage when that layer owns the behavior.
- Use the standard isolated DHF fixture for product tests:
  - `test_dhf_root` from `tests/sys/conftest.py`
- Test IDs follow `TC-SYS-NNN-NNN` pattern. Always include `@test_id:` and
  `@links:` docstring tags; add `@reviewer:`, `@review_status:`, `@review_date:`
  when the test has been design-reviewed.
- External test-result integration crosses the repository boundary via JUnit XML.
  - test frameworks emit XML
  - `compliantflow` imports and persists the results

### JUnit XML contract

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

### pytest adapter docstring format

`tests/conftest.py` provides the pytest-specific adapter via an autouse fixture.
It reads `@`-tags from test docstrings and calls `record_property()` automatically
— no manual calls needed in individual tests.

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
`pytest.ini` uses `junit_family = xunit1` so per-testcase properties are preserved.

### Persisted evidence

Persisted verification evidence lives in `DHF/test-results/results.yaml`.
TC items are evidence records there, not standalone YAML item files under
`DHF/items/`. `ResultStore` is append-mode: `get_latest(tc_id)` returns the most
recent result; `get_history(tc_id)` returns all records newest-first.

## Standard Command Surface

Agents should reuse the existing commands already documented in the repository.

Primary analysis loop:

```bash
PYTHONPATH=.:DHF python -m compliantflow validate traceability
PYTHONPATH=.:DHF python -m compliantflow validate coverage UC:CRS CRS:SYS SYS:SYSARCH
PYTHONPATH=.:DHF python -m compliantflow validate compliance IEC_62304 --governance-dir governance
PYTHONPATH=.:DHF python -m compliantflow cr check-status <CR-ID>
PYTHONPATH=.:DHF python -m compliantflow cr generate-report <CR-ID>
PYTHONPATH=.:DHF python -m compliantflow traceability matrix CRS SYS SRS
PYTHONPATH=.:DHF python -m compliantflow traceability chain SYS-001
```

Primary DHF/data loop:

```bash
PYTHONPATH=.:DHF python -m utils validate schema
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item get SYS-001
PYTHONPATH=.:DHF python -m utils item create --type SYS --data '{"title": "My req", "category": "Functional"}'
PYTHONPATH=.:DHF python -m utils item update SYS-001 --data '{"title": "Updated title"}'
PYTHONPATH=.:DHF python -m utils item delete SYS-001
PYTHONPATH=.:DHF python -m utils item transitions <CR-ID>
PYTHONPATH=.:DHF python -m utils item transition <CR-ID> approved --by "Alice"
PYTHONPATH=.:DHF python -m utils doc generate ALL
PYTHONPATH=.:DHF python -m utils doc export ALL
```

Test result integration:

```bash
PYTHONPATH=.:DHF python -m compliantflow test import results.xml --format junit --tester "GitHub Actions" --run-id 123 --run-url https://... --commit abc123
PYTHONPATH=.:DHF python -m compliantflow test status TC-SYS-001
PYTHONPATH=.:DHF python -m compliantflow test list --status PASS
```

Primary verification loop:

```bash
PYTHONPATH=.:DHF .venv/bin/pytest DHF/utils/tests/ -q
PYTHONPATH=.:DHF .venv/bin/pytest tests/sys/ tests/crs/ -q
```

Use narrower test targets only while iterating. Before merge, the full product
test suites still govern.
