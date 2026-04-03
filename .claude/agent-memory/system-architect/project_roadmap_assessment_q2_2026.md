---
name: Roadmap Architecture Assessment Q2 2026
description: Assessment of CompliantFlow architecture against v1.3.0/v2.0/v2.x roadmap, conducted 2026-04-02; updated 2026-04-03
type: project
---

Assessment conducted 2026-04-02. All v1.3.0 structural changes are now complete (2026-04-03).

**How to apply:** Reference this before significant feature design work for v2.0.0+.

## v1.3.0 structural changes — ALL DONE

1. ✅ LLM backend extracted: `compliantflow/backends/llm.py` — `LLMBackend` Protocol, `GeminiBackend`, `OllamaBackend`, `get_default_backend()`
2. ✅ `ComplianceReport` has `run_id`, `timestamp`, `commit_sha`, `governance_version` with Optional defaults
3. ✅ `DHFAdapter` protocol has `record_compliance_run` and `get_compliance_runs`
4. ✅ `ResultStore` is append-mode; `{tc_id: [record, ...]}` with transparent migration
5. ✅ `cr_git_evidence` check type added to PolicyEngine dispatch table
6. ✅ ID write-protection at adapter layer: `create_item` auto-generates, `update_item` raises on id change
7. ✅ `PolicyEngine` cached per (group_id, governance_dir) on `CompliantFlowCore`
8. ✅ Document index built at adapter init (O(1) lookup vs. rglob scan)

## v2.0.0 architectural considerations (Q3 2026)

- **Release gate**: `check_release_readiness(rel_id)` method on `CompliantFlowCore` — read-only, belongs in compliantflow CLI. Evaluates REL item's criteria against current DHF state.
- **Defect hook**: DEF lifecycle integration with CI. When a DEF is open/unresolved, a compliance check should fail. Likely a new `defect_open` check type in PolicyEngine.
- **ISO 14971**: New governance YAML. Risk management process checks. Will need `risk_mitigation_complete` check type or reuse `trace_coverage` (RISK→RCM coverage).
- **Multi-DHF**: `CompliantFlowCore` currently takes a single adapter. Future: accept list of adapters or a router. Do NOT change the constructor now — wait for a real use case.

## Structural debt to watch

- `LocalDHFAdapter._doc_index` is built once at init. If documents are added/removed without re-initializing the adapter, the index goes stale. Acceptable for CLI use (short-lived process); may need a `refresh_doc_index()` for long-lived server use.
- `ComplianceStore` and `ResultStore` both do their own YAML append logic. Could be unified into a generic `AppendStore` if a third store type is needed.
