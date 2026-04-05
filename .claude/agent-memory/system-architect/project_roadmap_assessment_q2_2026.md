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
- **ISO 14971**: ✅ CR-023 DONE (2026-04-02). `governance/ISO_14971.yaml` written. 30 policies total; 20 automated / 10 manual. No new check types required — existing check types cover all automation. Two DHF data model gaps identified (see below). New document dependencies: `risk_management_plan.md`, `risk_management_report.md`.

### ISO 14971 DHF data model gaps (RISK / RCM schemas)
1. **RISK**: No `intended_use_reference` link field — ISO 14971 §5.2 expects traceability from RISK items back to the hazardous situation's context (use cases). Workaround: `trace_coverage` RISK→UC is currently not enforced; policy 5.2.a checks `item_existence` UC instead. A `links` field on RISK pointing to UC would enable full traceability. Not blocking for v2.0.0 — document as tech debt.
2. **RCM `implementation_status`**: Current allowed values are `Planned / Implemented / Verified`. Policies 7.2.a and 7.6.b check `attribute_value` for `Implemented` and `Verified` respectively — this works today but means both checks cannot pass simultaneously (a single RCM cannot be both Implemented AND Verified if only one value is stored). **Recommended fix**: make `implementation_status` a multi-select or split into `implementation_status` + `verification_status` (separate fields). This is a schema change, must be a CR.
- **Multi-DHF**: `CompliantFlowCore` currently takes a single adapter. Future: accept list of adapters or a router. Do NOT change the constructor now — wait for a real use case.

## Structural debt to watch

- `LocalDHFAdapter._doc_index` is built once at init. If documents are added/removed without re-initializing the adapter, the index goes stale. Acceptable for CLI use (short-lived process); may need a `refresh_doc_index()` for long-lived server use.
- `ComplianceStore` and `ResultStore` both do their own YAML append logic. Could be unified into a generic `AppendStore` if a third store type is needed.
