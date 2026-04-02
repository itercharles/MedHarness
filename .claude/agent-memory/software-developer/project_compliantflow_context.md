---
name: CompliantFlow project context
description: Core architecture, patterns, and conventions for the CompliantFlow codebase
type: project
---

CompliantFlow is a Docs-as-Code ALM platform for medical devices. DHF items live as YAML files under DHF/items/. The Python backend has two CLIs: compliantflow (read-only analysis) and utils (data CRUD).

**Why:** Medical device compliance (IEC 62304, IEC 82304-1) requires audit trail — git history serves as the approval/audit mechanism for requirement items (UC, CRS, SYS, etc.).

**How to apply:** Always distinguish read-only analysis (compliantflow/) from data mutation (DHF/utils/). Never add mutation methods to CompliantFlowCore. New CLI commands in compliantflow/cli.py must use the `_make_core()` helper pattern and pass `ctx.obj["dhf"]` through click context.

Key patterns:
- All new check types registered in `PolicyEngine.checks` dict in `compliantflow/policy.py`
- Check functions return `Tuple[bool, str, Optional[Dict]]` (passed, details, evidence)
- `ResultStore` in `DHF/utils/result_store.py` is the pattern for persistence stores — replicate for `ComplianceStore`
- `LocalDHFAdapter._result_store` is wired in `__init__` from config: `self._result_store = ResultStore(self._dhf_root, result_store_cfg)`
- Protocol in `compliantflow/adapters/protocol.py` uses `@runtime_checkable` — adding methods there requires updating all adapter implementations
- Test fixtures: `test_dhf_root` creates isolated temp DHF; `governance_dir` is `test_dhf_root.parent / "governance"`
- CR items have explicit lifecycle (draft → in_review → approved → implementing → completed)
- Graph edges go child→parent; G.successors = upstream, G.ancestors = downstream
