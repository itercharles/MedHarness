# Agent Environment

CompliantFlow is a Docs-as-Code ALM platform for medical device software. It manages
Design History File (DHF) items — requirements, risks, tests, change requests — stored
as YAML files under `DHF/items/`. The Python backend exposes a CLI for CI/CD integration
and a library API for tests.

## Sources Of Truth

| Source | What it owns |
|---|---|
| `README.md` | Repository layout and setup |
| `DHF/` | Project facts, config, documents, item state, verification evidence |
| `governance/` | Compliance policy definitions |
| `.github/workflows/ci-pipeline.yml` | Enforced acceptance path and merge gates |

Agent entrypoints by harness: `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex),
`GEMINI.md` (Gemini CLI), `.github/copilot-instructions.md` (Copilot),
`.cursor/rules/agent.mdc` (Cursor), `.windsurfrules` (Windsurf).

## Environment

```bash
# Virtual environment
.venv/

# Python path (required for all commands)
PYTHONPATH=.:DHF
```

## Key Invariants

These are non-obvious from reading the code and have caused errors before.

**Two-CLI split.** `CompliantFlowCore` (`compliantflow/`) is read-only — analysis,
traceability, compliance, reporting. DHF mutations (create, update, delete, lifecycle
transitions) go through `python -m utils`. Do not add write operations to
`CompliantFlowCore`.

**Graph edge direction.** Edges in `compliantflow/graph.py` run child → parent.
`descendants()` means business-upstream (toward requirements). `ancestors()` means
business-downstream (toward tests). This is the opposite of the natural reading.

**GitOps approval.** Requirement item types (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`,
`SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit
status field change needed. Feature branches mean draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions
via `python -m utils item transition`. These are not GitOps-approved.

**`get_all_items()` returns dicts.** Access fields with `item['id']`,
`item.get('status')`. The dict includes a computed `all_linked_uids` list for graph
traversal — use this, not `item.get('links')`, which does not exist.
