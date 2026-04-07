---
name: CompliantFlow Architecture Decisions
description: Key architectural decisions, constraints, and patterns in CompliantFlow
type: project
---

## DHFAdapter Protocol

`compliantflow/adapters/protocol.py` defines a structural Protocol (runtime_checkable). `LocalDHFAdapter` in `DHF/utils/local_adapter.py` implements it. Protocol includes `record_compliance_run` and `get_compliance_runs` (added v1.3.0).

**Why:** Separates read-only analysis (compliantflow core) from data mutations (DHF utils layer). Alternative backends can plug in without changing the engine.

## MultiDHFAdapter (CR-029, v2.1.0)

`compliantflow/adapters/multi.py` — `MultiDHFAdapter` implements `DHFAdapter` and routes across a `dict[slug, adapter]`. `CompliantFlowCore` is unchanged (still single-adapter). The CLI gains `--project slug:path` (repeatable) to activate multi-project mode; `--dhf` single-project mode is fully backward compatible.

**ID namespacing:** All item IDs and intra-project link fields (`all_linked_uids`, `satisfies`, `derives_from`, `affected_items`) are prefixed `slug::id` so the graph engine can resolve edges across projects without collision. Mutations route by parsing the slug prefix; un-namespaced UIDs go to the primary adapter (first entry).

**Design constraints:** compliance runs and `get_project_config()` delegate to the primary adapter only. Do NOT add cross-project graph merging without an explicit CR — projects are partitioned by default.

## Two-CLI Split

- `python -m compliantflow` (compliantflow/cli.py) — read-only analysis, traceability, compliance checks, CR check-status/generate-report, test import/status/list, PDF reports
- `python -m utils` (DHF/utils/cli.py) — item CRUD, lifecycle transitions, doc generation, test import/status/list/pull

Bulk approval is mutating → belongs in utils CLI. Release gate is read-only evaluation → belongs in compliantflow CLI.

## ID Generation (CR-006)

`create_item()` in `LocalDHFAdapter` always auto-generates IDs via `get_next_id()`. Any caller-supplied `id` in the data dict is silently stripped before generation. `update_item()` raises `ValidationError` if the caller attempts to change the `id` field. This is enforced at the adapter layer, not the domain model.

## PolicyEngine Check Dispatch

`policy.py` uses a dict-based dispatch table (`self.checks`) keyed by check name string. 10 check types registered. Adding a new check only requires a method + `self.checks[name] = method` in `__init__`. Manual policies (no `automation` block) are surfaced with `evidence_guidance` from governance YAML.

`PolicyEngine` is cached per `(group_id, governance_dir)` on `CompliantFlowCore` via `_get_policy_engine()` — avoids re-parsing governance YAML on repeated calls.

## LLM Abstraction

`compliantflow/backends/llm.py` defines `LLMBackend` Protocol with `generate(prompt) -> str`. `GeminiBackend` wraps `google.genai`; `OllamaBackend` uses `COMPLIANTFLOW_OLLAMA_URL` / `COMPLIANTFLOW_OLLAMA_MODEL` env vars. `get_default_backend()` picks Gemini if `GEMINI_API_KEY` is set, Ollama if URL is set, else `None`. Manual policies degrade gracefully when no backend is available.

## ResultStore

`DHF/utils/result_store.py` is **append-mode**: `{tc_id: [record, ...]}` with newest-first ordering. `record_execution()` prepends; `get_latest(tc_id)` returns most recent; `get_history(tc_id)` returns all. Transparent migration from old flat `{tc_id: record}` format on load.

## Compliance Run Persistence

`DHF/utils/compliance_store.py` appends compliance runs to `DHF/compliance-runs/<standard_id>.yaml`. `check_compliance(..., persist=True)` writes run with `run_id`, `timestamp`, `commit_sha`, `governance_version`. `ComplianceReport` domain model has these fields with `Optional` defaults.

## Document Index

`LocalDHFAdapter.__init__` builds `_doc_index: dict[str, Path]` from `rglob("*.md")` under `DHF/documents/`. `get_document(doc_id)` is a O(1) dict lookup. Index is rebuilt on adapter init only.

## Graph Edge Convention

NetworkX DiGraph, edge direction child→parent. `nx.descendants(G, id)` = business upstream (parents). `nx.ancestors(G, id)` = business downstream (children). All policy checks and `get_item_chain()` use this convention.

## Field Schema Gap (prerequisite for CR-039, CR-040, CR-041, CR-042)

`ProjectConfig` in the utils layer (`DHF/utils/models/config.py`) carries field-level constraints per doc type: required flag, allowed values (options), field format type. These are parsed from `DHF/config/doc_types/*.yaml`.

`ProjectSchema` (the compliantflow domain model) does NOT carry these constraints — it only knows item type codes, prefixes, and top-level lifecycle. This means the compliantflow analysis layer cannot describe what fields are valid for a given item type without accessing the utils layer directly, violating the layer boundary.

**Fix (CR-039):** Extend `ItemTypeSchema` with a `fields: List[FieldConstraint]` structure populated by `LocalDHFAdapter.get_project_config()`. Add the method to the DHFAdapter protocol. `MultiDHFAdapter` delegates to the primary adapter. This unblocks:
- CR-040: AI Agent Context Package (needs field schema for context output)
- CR-041: Draft Item Pre-Validation (needs field schema for schema validation)
- CR-042: Compliance Status Summary (needs traceability matrix config from global.yaml)

**Do not implement CR-040 or CR-041 before CR-039 is merged.**

## New Check Type Pattern (CR-045)

Adding new policy.automation.check types (e.g. `soup_vulnerability` for CR-045) requires: (1) a method on `PolicyEngine`; (2) registration in `self.checks` dict in `__init__`. No other changes. The governance YAML references the new check type by string name. Follow the existing 10-check dispatch pattern exactly.

## Compliance-Aware PR Review Agent (CR-049)

This is the first agentic capability in CompliantFlow — diff-aware, LLM-backed, suggestion layer only. Key architectural constraints:
- Must NOT produce a pass/fail exit code used as a gate. The existing CI gate is the authoritative blocker. This is a suggestion layer only.
- Diff parsing scoped to DHF YAML changes (`DHF/items/`) only in the first CR. Source code → DHF item mapping is deferred.
- Reuses `GeminiBackend`/`OllamaBackend` via existing `LLMBackend` protocol — no new LLM dependencies.
- Delivered as `compliantflow review-pr --diff-file <path>` + optional GitHub Actions wrapper that posts output as PR comment.
- Prompt engineering quality is the primary implementation risk. Must be validated against representative PR diffs.

## CI Pipeline Structure

Single `ci-pipeline.yml` with 5 phases. Phase 0 (PR only) validates CR IDs in PR title. Phases 1–4 run on both PR and push-to-main via `if: always() && !failure() && !cancelled()` on phase1. Phase 3.5 generates merged CR-PR evidence report for all CRs. Phase 4 imports JUnit XML artifacts before running compliance checks.
