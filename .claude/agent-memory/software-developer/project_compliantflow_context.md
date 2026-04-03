---
name: CompliantFlow project context
description: Core architecture, patterns, and conventions for the CompliantFlow codebase
type: project
---

CompliantFlow is a Docs-as-Code ALM platform for medical devices. DHF items live as YAML files under DHF/items/. The Python backend has two CLIs: compliantflow (read-only analysis) and utils (data CRUD).

**Why:** Medical device compliance (IEC 62304, IEC 82304-1) requires audit trail — git history serves as the approval/audit mechanism for requirement items (UC, CRS, SYS, etc.).

**How to apply:** Always distinguish read-only analysis (compliantflow/) from data mutation (DHF/utils/). Never add mutation methods to CompliantFlowCore. New CLI commands in compliantflow/cli.py must use the `_make_core()` helper pattern and pass `ctx.obj["dhf"]` through click context.

## Key patterns

- All new check types registered in `PolicyEngine.checks` dict in `compliantflow/policy.py`
- Check functions return `Tuple[bool, str, Optional[Dict]]` (passed, details, evidence)
- `ResultStore` in `DHF/utils/result_store.py` is append-mode (`{tc_id: [record, ...]}`, newest-first); `get_latest(tc_id)`, `get_history(tc_id)`
- `ComplianceStore` in `DHF/utils/compliance_store.py` appends runs to `DHF/compliance-runs/<standard_id>.yaml`
- `LocalDHFAdapter._result_store` and `._compliance_store` wired in `__init__`
- Protocol in `compliantflow/adapters/protocol.py` uses `@runtime_checkable` — adding methods requires updating all adapter implementations
- Test fixtures: `test_dhf_root` creates isolated temp DHF; `governance_dir` is `test_dhf_root.parent / "governance"`
- `populate_test_dhf()` uses `ItemSaver` directly (not `adapter.create_item`) so hardcoded fixture IDs are preserved
- CR items have explicit lifecycle (draft → in_review → approved → implementing → completed)
- Graph edges go child→parent; `nx.descendants(G, id)` = business upstream; `nx.ancestors(G, id)` = business downstream

## ID rules (CR-006)

`create_item()` always auto-generates IDs — any `id` in the input dict is stripped. `update_item()` raises `ValidationError` if `id` changes. Never pass `id` in `data` to `create_item()` in production code. In test fixtures, use `ItemSaver.save()` directly to write items with known IDs.

## LLM backend

`compliantflow/backends/llm.py` — `LLMBackend` Protocol, `GeminiBackend`, `OllamaBackend`. `get_default_backend()` checks `GEMINI_API_KEY` then `COMPLIANTFLOW_OLLAMA_URL`. Pass `llm_backend=get_default_backend()` when instantiating `PolicyEngine` directly; `CompliantFlowCore` handles this internally.

## CI pipeline

Single `ci-pipeline.yml`: Phase 0 (PR-only CR gate) → Phase 1 (DHF utils tests) → Phase 2 (SYS tests) → Phase 3 (CRS tests) → Phase 3.5 (CR-PR evidence report) → Phase 4 (validation, test import, compliance, PDF reports). Test results flow: JUnit XML uploaded as artifact in phases 1–3, downloaded and imported in Phase 4.
