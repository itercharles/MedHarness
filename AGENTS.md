# AGENTS.md

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
.venv/            # virtual environment
PYTHONPATH=.:DHF  # required for all commands
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

---

## Change Workflow

1. **Orient** — confirm which layer is being changed: data, analysis, governance, or tests.
2. **Modify** — keep changes in the layer that owns the behavior. If a design document
   changes, update the corresponding DHF items. If a test changes, verify `@links:` tags
   still point to the correct items.
3. **Validate locally** — run the smallest relevant test first, then the governing suite
   for that layer before merge.
4. **Check merge gates** — use the CI phases in `ci-pipeline.yml` as the acceptance model.

## Validation

| Change type | Validation |
|---|---|
| Code-local | Nearest focused test |
| Product behavior | Owning suite + `tests/sys/ tests/crs/` |
| DHF data layer | `DHF/utils/tests/` |
| Compliance engine or governance | `tests/sys/test_sys_005_compliance.py` |

Do not run full compliance execution as a default step. It is a verification step for
compliance-related changes only.

## CR Workflow

CR items use two statuses: `planned` (identified, not yet implemented) and `closed`
(implemented and merged to `main`).

1. Confirm the CR exists and is `planned`. If not, create it with
   `python -m utils item create --type CR` before writing any code.
2. If the CR involves new tests, read `tests/fixtures/test_data.py` and the relevant
   doc type configs first. Field mismatches in test fixtures are the most common source
   of iteration in this repo.
3. Make changes in the owning layer.
4. Set the CR to `closed` and include that YAML change in the same commit as the
   implementation.
5. Validate locally, then commit directly to `main` for solo work. Open a PR when
   changes warrant review — include the CR ID in the PR title so Phase 0 CI can
   extract it.

## CI Model

Five phases defined in `.github/workflows/ci-pipeline.yml`:

1. Phase 0: CR validation (PR title must contain a CR ID)
2. Phase 1: DHF utility tests
3. Phase 2: SYS API tests
4. Phase 3: CRS API tests
5. Phase 3.5+: evidence and reporting flows

## Specialized Agents (Claude Code only)

Three sub-agents live in `.claude/agent-memory/`. The main session acts as
orchestrator — consult agents, synthesize outputs, make decisions.

**product-manager** — scope, roadmap, business context.
**system-architect** — system design and layer boundaries.
**software-developer** — implementation patterns and conventions.

**New feature / CR:** consult product-manager + system-architect → write a plan spec → implement.
**Bug fix:** consult software-developer → implement.
**Architectural decision:** consult system-architect + product-manager → write a plan spec → implement.

### Plan Spec

Write after consulting agents, before writing code. Required for any new feature CR or
any fix touching more than one file or layer.

Must contain: (1) scope; (2) affected files by layer; (3) non-obvious design decisions;
(4) test approach; (5) explicit out-of-scope constraints.

Write inline in the session. Do not save to disk unless the user asks.

## Design Rules

- Prefer commands over frameworks.
- Prefer existing tests over new harness-only tests.
- Keep harness entrypoints as thin pointers to this file.
- Put new shared guidance here; add content to a harness entrypoint only if it is
  genuinely specific to that harness.
