# Testing Strategy

**Owner:** Engineering Lead
**Status:** Active
**Last reviewed:** 2026-04-22

This document records CompliantFlow's testing approach: what gets tested, at what level, and how test evidence is linked to DHF items. Update when test infrastructure, layer structure, or evidence conventions change.

---

## Test Layers

| Layer | Location | What it covers |
|---|---|---|
| SYS tests | `tests/sys/` | API-facing product behaviour, one test file per SYS item group |
| CRS tests | `tests/crs/` | End-to-end scenario coverage at CRS level |
| DHF utils tests | `compliantflow-dhf/DHF/utils/tests/` | Data layer: item CRUD, lifecycle transitions, schema validation |

There are no separate unit tests for internal functions — test behaviour at the layer boundary, not implementation details.

---

## Test ID Convention

Format: `TC-SYS-NNN-NNN` (sys layer) or `TC-CRS-NNN-NNN` (CRS layer).

Every test function name must embed the TC ID:

```python
def test_TC_SYS_027_001_init_creates_dhf_structure(tmp_path):
```

---

## Docstring Format

Each test requires a docstring with `@links` pointing to the DHF item being covered:

```python
def test_TC_SYS_027_001_init_creates_dhf_structure(tmp_path):
    """
    TC-SYS-027-001: compliantflow init creates expected DHF directory structure

    @test_id: TC-SYS-027-001
    @links: SYS-027
    """
```

`tests/conftest.py` autouse fixture reads `@`-tags and calls `record_property()` automatically. Tests with no TC ID are skipped on DHF import.

---

## JUnit XML Contract

The CI pipeline exports test results to JUnit XML and imports them into the DHF via post-merge CI. The contract:

```xml
<testcase name="test_TC_SYS_027_001_init_creates_dhf_structure">
  <properties>
    <property name="compliantflow.id"    value="TC-SYS-027-001"/>
    <property name="compliantflow.links" value="SYS-027"/>
  </properties>
</testcase>
```

`compliantflow.id` falls back to regex from the function name if the `@test_id` tag is absent. The `@links` tag is required for traceability — missing links produce orphaned test evidence.

---

## Fixtures

- `test_dhf_root` — isolated DHF root (from `tests/sys/conftest.py`); use for all product tests that need a DHF
- `governance_dir` — path to the governance directory
- **Read `tests/fixtures/test_data.py` before writing new fixture data.** Field mismatches between fixtures and doc type configs are the most common source of test iteration.

---

## Test Evidence Storage

Persisted evidence lives in `compliantflow-dhf/DHF/test-results/results.yaml`. TC items are evidence records there — they are not standalone YAML files under `DHF/items/`. `ResultStore.get_latest(tc_id)` returns the most recent result for a given TC ID.

---

## DHF Impact

New or modified tests require:

- A `TC` item in `compliantflow-dhf/DHF/items/` with `@links` to the relevant `SYS` or `CRS` item
- The test function name and docstring to match the TC ID

Tests that cover new system behaviour also require the corresponding `SYS` and `SRS` items to exist and be linked.

---

## What Not to Test

- Internal implementation details (private functions, intermediate graph state)
- Compliance checks that invoke an external LLM — these are not run as default validation; use mocks or skip in CI
- Filesystem side effects beyond the isolated `test_dhf_root` fixture

---

## Running Tests Locally

```bash
# All tests
.venv/bin/python -m pytest tests/ -q

# Specific file
.venv/bin/python -m pytest tests/sys/test_sys_027_init.py -q

# DHF utils tests (from DHF repo root)
cd compliantflow-dhf
PYTHONPATH=.:DHF python -m pytest DHF/utils/tests/ -q
```
