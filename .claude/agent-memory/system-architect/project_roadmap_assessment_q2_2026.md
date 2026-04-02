---
name: Roadmap Architecture Assessment Q2 2026
description: Assessment of CompliantFlow architecture against v1.3.0/v2.0/v2.x roadmap, conducted 2026-04-02
type: project
---

Assessment conducted 2026-04-02 covering v1.3.0 (Q2 2026), v2.0.0 (Q3 2026), v2.x (Q4 2026+).

**Why:** Proactive assessment to identify structural debt before it compounds. Key findings saved here to inform future design work.

**How to apply:** Reference this before any significant feature design work to avoid re-litigating already-assessed questions.

## Critical findings

1. LLM backend is hard-wired to Gemini (`google.genai` import in policy.py `_run_semantic_batch`). Must extract an LLM backend abstraction in v1.3.0 or the Ollama fallback becomes a messy conditional.

2. ComplianceReport model (`domain/compliance.py`) lacks `run_id`, `timestamp`, `commit_sha`, `governance_version`. Must add these for persistence. Safe Pydantic extension with defaults.

3. DHFAdapter protocol lacks compliance run persistence methods (`save_compliance_run`, `list_compliance_runs`). Must add to protocol for multi-DHF support — otherwise persistence will be hardcoded to local filesystem.

4. ResultStore (`result_store.py`) stores only the latest result per TC. No run-level history. For DHF-as-record compliance runs, need either a separate RunStore or extend ResultStore with an append log.

5. The `cr_git_evidence` check type for PR-to-CR CI gate can be added to PolicyEngine dispatch table with zero structural changes.

6. Multi-DHF support will require `CompliantFlowCore` to accept a list of adapters or a router — the current single-adapter constructor is a future refactor point but does NOT need to change in v1.3.0.

7. The web UI backend gap: DHFAdapter protocol includes `create_item`, `update_item`, `delete_item` — mutations are already in the protocol. The read-only/mutation CLI split is a CLI convention, not a protocol constraint. A web UI can use the full adapter directly.

## Structural changes recommended for v1.3.0

- Extract LLM backend interface from policy.py (LLMBackend protocol with `generate(prompt) -> str`)
- Add persistence fields to ComplianceReport (run_id, timestamp, commit_sha, governance_version) with Optional defaults
- Add `save_compliance_run` / `list_compliance_runs` to DHFAdapter protocol
- Add `cr_git_evidence` check type to PolicyEngine
- Enforce ID write-protection at validation layer in loader.py
