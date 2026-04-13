# Agent Workflow

This document defines how an agent should operate inside the environment
described in [`docs/agent_environment.md`](agent_environment.md).

## Change Workflow

1. **Orient** — confirm which layer is being changed: data, analysis, governance, or tests.
2. **Modify** — keep changes in the layer that owns the behavior. If a design document
   changes, update the corresponding DHF items. If a test changes, verify `@links:` tags
   still point to the correct items.
3. **Validate locally** — run the smallest relevant test first, then the governing suite
   for that layer before merge.
4. **Check merge gates** — use the CI phases in `ci-pipeline.yml` as the acceptance model.

## Validation Usage

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

When work is tied to a change request:

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

## Specialized Agents

Three sub-agents live in `.claude/agent-memory/`. The main session acts as
orchestrator — consult agents, synthesize outputs, make decisions. Never delegate
synthesis to a sub-agent.

**product-manager** — scope, roadmap, business context. Use when scoping a CR,
validating roadmap fit, or evaluating trade-offs.

**system-architect** — system design and layer boundaries. Use when deciding which
layer owns a change, extending `DHFAdapter`, or assessing architectural feasibility.

**software-developer** — implementation patterns and conventions. Use when implementing
a feature or fix.

### Orchestration Patterns

**New feature / CR:** consult product-manager + system-architect (in parallel if scope
is clear) → write a plan spec → implement.

**Bug fix:** consult software-developer → consult system-architect only if fix crosses
layers → implement.

**Architectural decision:** consult system-architect + product-manager in parallel →
write a plan spec → implement.

### Plan Spec

Write after consulting agents, before writing code. Required for any new feature CR or
any fix touching more than one file or layer. Skip for single-file isolated changes.

Must contain: (1) scope — one sentence, what's in and what's out; (2) affected files by
layer; (3) non-obvious design decisions and why; (4) test approach; (5) explicit
out-of-scope constraints.

Write inline in the session. Do not save to disk unless the user asks.

### Memory Update Protocol

Update agent memory after completing significant work — only when the work reveals
something non-obvious that the agent would otherwise re-derive wrongly.

| What changed | Update |
|---|---|
| CR completed or scope changed | `product-manager/project_crs.md` |
| Feature shipped or roadmap shifted | `product-manager/project_features.md` |
| Architectural decision made | `system-architect/project_architecture_decisions.md` |
| New coding pattern established | `software-developer/project_compliantflow_context.md` |

## CI Model

Five phases defined in `.github/workflows/ci-pipeline.yml`:

1. Phase 0: CR validation (PR title must contain a CR ID)
2. Phase 1: DHF utility tests
3. Phase 2: SYS API tests
4. Phase 3: CRS API tests
5. Phase 3.5+: evidence and reporting flows

Treat these as the real acceptance path. Local iteration mirrors them, not replaces them.

## Design Rules

- Prefer commands over frameworks.
- Prefer existing tests over new harness-only tests.
- Prefer existing docs over new parallel docs.
- Put new shared agent guidance in `docs/agent_environment.md` or `docs/agent_workflow.md`.
- Keep `AGENTS.md`, `CLAUDE.md`, and other harness entrypoints as thin pointers.
- Prefer task-local context over loading the full compliance corpus.
- Prefer CI alignment over custom local gates.
