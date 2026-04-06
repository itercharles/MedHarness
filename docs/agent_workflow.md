# Agent Workflow

This document defines how an agent should operate inside the environment
described in
[`docs/agent_environment.md`](agent_environment.md).

It answers:
- how to keep generation scoped and use compliance checks correctly
- how to make and validate changes
- how PR and CR handling should work
- how to use the existing CI path

## Change Workflow

Use this sequence for normal work:

1. Orient
   - Read `AGENTS.md` or `CLAUDE.md`.
   - Read [`docs/agent_environment.md`](agent_environment.md).
   - Confirm which layer is being changed: data, analysis, governance, or tests.
   - Keep the working context narrow; do not load the full compliance set unless the task is explicitly about compliance logic.
2. Modify
   - Keep changes in the layer that owns the behavior.
   - Avoid duplicating repository knowledge in new docs or scripts.
   - If a design document changes, update the corresponding DHF items (requirements,
     architecture, SWDD) to keep traceability intact.
   - If a test changes, update the linked DHF test records and verify `@links:` tags
     still point to the correct items.
3. Validate locally
   - Run the smallest relevant command or test first.
   - Then run the governing suite for that layer.
   - For normal product changes, prefer targeted pytest coverage first, then `tests/sys/ tests/crs/` before merge.
   - Use the compliance CLI only when the task actually changes or debugs compliance behavior.
4. Check merge gates
   - Use the CI phases in `ci-pipeline.yml` as the acceptance model.
   - Do not add sidecar gates unless the repo workflow has changed.
5. Handoff
   - Summarize what changed, what was validated, and any remaining risk.

## Validation Usage

Use the lightest validation that matches the task:

- code-local change
  - run the nearest focused test first
- product behavior change
  - run the owning suite, then `tests/sys/ tests/crs/` before merge
- DHF data-layer change
  - run `DHF/utils/tests/`
- compliance-engine or governance change
  - run focused compliance coverage in `tests/sys/test_sys_005_compliance.py`
  - run the compliance CLI against the relevant policy group when needed

Do not treat full compliance execution as a default generation step. It is a
verification step for compliance-related changes.

## PR And CR Workflow

CR items have two states: `planned` (identified, not yet merged) and `completed`
(merged to `main`). The PR merge itself is the approval event — no intermediate
approval states are required.

When work is tied to a change request:

1. Confirm the CR exists and is `planned`. If the CR does not exist yet, create
   it with `python -m utils item create --type CR` before writing any code.
2. If the CR involves new tests, read `tests/fixtures/test_data.py` and the
   relevant doc type configs before writing any test code. Confirm which fields
   are allowed per schema — test fixture mismatches are the most common source
   of iteration in this repo.
3. Make the code and document changes in the owning layer.
4. Transition the CR to `completed` and include that YAML change in the same
   commit as the implementation. The CR status lands on `main` at merge time —
   do not defer it to after merge.
5. Validate locally with the existing commands and test suites.
6. Open a PR that includes the CR ID in the title, for example:

```bash
feat(<CR-ID>): update compliance workflow
```

7. **Immediately after opening the PR, begin monitoring.** Do not treat PR
   creation as a handoff point. Stay in the session and:
   - Poll CI status until all checks pass or a failure requires action.
   - Check for review comments and address them with follow-up commits.
   - Do not move on to other work until the PR is merged or explicitly handed
     off by the user.
8. Always merge with squash: one commit per PR on main.

The PR title requirement matters because Phase 0 extracts CR IDs from the PR
title and fails immediately if none are present.

### GitHub tooling

Use the `gh` CLI for all GitHub interactions (creating PRs, checking CI status,
merging). It is available and preferred over the GitHub MCP tools, which require
separate authentication.

- Create PRs: `gh pr create --title "..." --base main --body "..."`
- Check CI: `gh pr checks <number> --repo <owner>/<repo>`
- Merge with squash: `gh pr merge <number> --squash --delete-branch`

### Branch naming

- `feature/`, `fix/`, `refactor/` — human-initiated work
- `claude/` — Claude Code sessions

## Specialized Agents

Three sub-agents are available in `.claude/agent-memory/`. Each carries
persistent memory about their domain. The main session acts as orchestrator —
it consults agents, synthesizes their outputs, and makes decisions. Never
delegate synthesis to a sub-agent.

### Agent Roles

**product-manager** — scope, roadmap, and business context

- When to use: scoping a CR, validating roadmap fit, understanding customer
  trade-offs, evaluating competitive positioning.
- Memory covers: product overview, feature inventory, active CRs, strategy,
  competitive landscape, full roadmap through v3.0.0.
- Skip for: implementation patterns, architectural decisions.

**system-architect** — system design and layer boundaries

- When to use: deciding which layer owns a change (`compliantflow/` vs.
  `DHF/utils/`), extending the `DHFAdapter` protocol, designing a new
  subsystem, assessing architectural feasibility.
- Memory covers: `DHFAdapter` protocol, two-CLI split rationale,
  `PolicyEngine` dispatch, `ResultStore`, `ComplianceStore`, LLM abstraction,
  graph edge conventions, CI pipeline structure, Q2 2026 roadmap assessment.
- Skip for: product prioritization, line-level implementation details.

**software-developer** — implementation patterns and conventions

- When to use: implementing a feature or fix — which patterns to follow, how
  to write test fixtures, which CLI to extend.
- Memory covers: read-only vs. mutation split, `PolicyEngine` check
  registration, `ResultStore` semantics, graph edge direction, ID generation
  rules, test fixture conventions.
- Skip for: product strategy, architectural boundary decisions.

### Orchestration Patterns

Use the pattern that matches the task. Run agents in parallel when their inputs
are independent; sequentially when the output of one informs the next.

**New feature / CR implementation**

1. Consult `product-manager` — validate scope, roadmap fit, priority.
2. Consult `system-architect` — identify affected layer(s), validate design.
   (Steps 1 and 2 can run in parallel if scope is already clear.)
3. Implement using `software-developer` patterns and conventions.

**Bug fix / defect**

1. Consult `software-developer` — affected patterns, conventions.
2. Consult `system-architect` only if the fix crosses architectural boundaries.
   Skip `product-manager` unless the defect has customer-facing scope impact.

**Architectural decision** (new protocol method, new layer, new abstraction)

1. Consult `system-architect` and `product-manager` in parallel — feasibility
   and roadmap alignment.
2. Synthesize both outputs before designing the solution.

**Roadmap / planning**

1. Consult `product-manager` — primary source for prioritization and strategy.
2. Consult `system-architect` for feasibility constraints on specific items.

### Memory Update Protocol

After completing significant work, update the affected agent's memory so future
sessions start with accurate context. Use judgment — only update when the work
reveals something non-obvious that the agent would otherwise re-derive wrongly.

| What changed | Update |
|---|---|
| New CR completed or scope changed | `product-manager/project_crs.md` |
| New feature shipped or roadmap shifted | `product-manager/project_features.md` or `project_strategy.md` |
| Architectural decision made (new protocol method, layer boundary changed) | `system-architect/project_architecture_decisions.md` |
| New coding pattern established or existing pattern corrected | `software-developer/project_compliantflow_context.md` |

Do not update agent memory for routine implementation work that is already
captured in code and commit history.

---

## CI Model

GitHub Actions already defines the workflow that matters:

1. Phase 0: CR validation for pull requests
2. Phase 1: DHF utility tests
3. Phase 2: SYS API tests
4. Phase 3: CRS API tests
5. Phase 3.5 and Phase 4+: evidence and reporting flows

Agents should treat these as the real acceptance path. Local iteration should
mirror them, not replace them.

## Design Rules

When adding new agent support in this repository:

- prefer commands over frameworks
- prefer existing tests over new harness-only tests
- prefer existing docs over new parallel docs
- put new shared agent guidance in `docs/agent_environment.md` or `docs/agent_workflow.md`
- keep `AGENTS.md` and `CLAUDE.md` as thin entrypoints unless content is model-specific
- when the working workflow changes (new CI phase, new validation sequence, branch
  conventions, PR/CR process), update `docs/agent_workflow.md`
- when the project environment or directory structure changes (new layer, new tooling,
  new command surface, new invariant), update `docs/agent_environment.md`
- prefer task-local context over loading the full compliance corpus
- when changing compliance behavior, prefer relevant real governance inputs over synthetic fixtures
- prefer CI alignment over custom local gates

If a proposed harness change introduces a new execution path, ask whether the
same goal can be reached by tightening the existing command, test, or CI
workflow instead.
