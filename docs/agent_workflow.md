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

When work is tied to a change request:

1. Transition the CR into an allowed implementation state before code work.
   - Sequence: `draft → in_review → approved → implementing`
   - Before the first transition, check blocking criteria and pre-populate all
     required fields (`impact_assessment`, `assigned_to`, etc.) in the CR YAML.
     Run `python -m utils item transitions <CR-ID>` to see what is required.
     Filling fields after a failed transition wastes a round trip.
2. If the CR involves new tests, read `tests/fixtures/test_data.py` and the
   relevant doc type configs before writing any test code. Confirm which fields
   are allowed per schema — test fixture mismatches (missing fields, wrong
   values) are the most common source of iteration in this repo.
3. Make the code and document changes in the owning layer.
3. If this PR fully implements the CR, transition the CR to `completed` and
   include that YAML change in the PR commit. The CR status lands on main at
   merge time alongside the code — do not defer it to after merge.
4. Validate locally with the existing commands and test suites.
5. Open a PR that includes the CR ID in the title, for example:

```bash
feat(<CR-ID>): update compliance workflow
```

6. While the PR is open, continuously monitor for review comments and address
   them with follow-up commits before merging.
7. Let the existing CI phases enforce the merge path. Monitor the PR until all
   checks pass — do not hand off and move on.
8. Always merge with squash: one commit per PR on main.

`cr check-status` (Phase 0 CI gate) accepts CRs in `approved`, `implementing`,
or `completed` state.

The PR title requirement matters because Phase 0 extracts CR IDs from the PR
title and fails immediately if none are present.

### GitHub tooling

The `gh` CLI is **not available**. Use `git push` to push branches and the
GitHub MCP tools (`mcp__github__*`) for all GitHub interactions (creating PRs,
checking CI status, merging).

- Merge PRs with squash: `mcp__github__merge_pull_request` with `merge_method: squash`.
- Delete the branch manually after merge (the GitHub MCP server has no
  delete-branch tool; use the GitHub UI or `git push origin --delete <branch>`).

### Branch naming

- `feature/`, `fix/`, `refactor/` — human-initiated work
- `claude/` — Claude Code sessions

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
