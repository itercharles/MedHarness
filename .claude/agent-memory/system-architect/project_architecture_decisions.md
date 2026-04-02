---
name: CompliantFlow Architecture Decisions
description: Key architectural decisions, constraints, and patterns in CompliantFlow
type: project
---

## DHFAdapter Protocol

`compliantflow/adapters/protocol.py` defines a structural Protocol (runtime_checkable). LocalDHFAdapter in `DHF/utils/local_adapter.py` implements it. The protocol has 14 methods but does NOT include `save_compliance_run`, `list_compliance_runs`, or any persistence method for compliance results — this is a gap for the v1.3.0 roadmap.

**Why:** Separates read-only analysis (compliantflow core) from data mutations (DHF utils layer).

## Two-CLI Split

- `python -m compliantflow` (compliantflow/cli.py) — read-only analysis, traceability, compliance checks, report generation
- `python -m utils` (DHF/utils/cli.py) — item CRUD, lifecycle transitions, doc generation

Bulk approval and release gate CLI commands need to decide which CLI they belong to. Bulk approval is mutating → belongs in utils CLI. Release gate is read-only evaluation → belongs in compliantflow CLI.

## PolicyEngine Check Dispatch

`policy.py` uses a dict-based dispatch table (`self.checks`) keyed by check name string. Adding a new check type (e.g., `cr_git_evidence`) only requires adding a method and registering it in `__init__`. No structural changes needed.

Manual policies (no `automation` block) are evaluated by checking `policy.status == 'approved'`. The `manual: true` flag in governance YAML maps to absence of automation block.

## LLM Coupling

`_run_semantic_batch()` in policy.py has a hard dependency on `google.genai` (Gemini). The API key check (`os.environ.get("GEMINI_API_KEY")`) is the only abstraction. If the key is absent, semantic checks fail gracefully with an error message. Swapping to Ollama requires extracting an LLM backend interface.

## ResultStore

`DHF/utils/result_store.py` stores only the latest result per TC ID in a flat YAML file (`DHF/test-results/results.yaml`). No history, no run-level records, no compliance-run persistence. This is a gap for v1.3.0 compliance run persistence.

## ComplianceReport Domain Model

`compliantflow/domain/compliance.py` — ComplianceReport has no `run_id`, `timestamp`, `commit_sha`, or `governance_version` fields. Adding these for persistence/history requires extending this model, which is safe since it is Pydantic and all consumers use `.model_dump()`.

## ID Generation

`DHF/utils/id_generator.py` — `get_next_id()` auto-generates IDs. The `create_item()` in LocalDHFAdapter generates IDs server-side if not provided. However, the protocol allows callers to pass any `id` in data — write-protection at the validation layer does not yet exist.

## Graph Edge Convention

NetworkX DiGraph, edge direction child→parent. `nx.descendants(G, id)` = business upstream. `nx.ancestors(G, id)` = business downstream. All policy checks use `successors`/`predecessors` directly.
