# Pre-Analyze Checklist

Review this checklist before implementing any user request.

## 1. Request Framing

- What user outcome is actually being asked for?
- Which change class best fits this request?
  - `docs/process`
  - `infra/devops`
  - `bugfix`
  - `feature`
  - `architecture`
- Which layer owns the change: `compliantflow/` (CLI, compliance engine, reporting), `scripts/`, `AI-harness/`, or repository-wide CI / docs?

Expected gate by class:

- `docs/process`: doc consistency check, no DHF by default, no PR by default
- `infra/devops`: validation + rollback thinking + observability expectations
- `bugfix`: regression test expectation, CR required
- `feature`: branch, PR, DHF assessment, automated validation, manual test plan, CR required
- `architecture`: branch, PR, DHF assessment, validation plan, CR required

## 2. Product Direction Check

- Is the request consistent with the product mission stated in `AI-harness/context.md`?
- Does it strengthen CompliantFlow's core value (compliance gate, DHF template, AI harness) or is it pulling in scope that doesn't fit?
- Should the request be narrowed because it conflicts with current focus?

If the request conflicts with product direction, state the conflict before implementation.

## 3. Technical Direction Check

- Is the request consistent with the two-CLI split (`compliantflow/` read-only; DHF mutations via `python -m utils`)?
- Does it preserve the separation between the product repo and the DHF repo?
- Does it add infrastructure or abstractions that will be hard to validate or maintain?
- Does it introduce assumptions about local paths, user environment, or external services?

If the request conflicts with technical direction, state the conflict before implementation.

## 4. DHF Impact Check

- Will this request modify product behavior, requirements, architecture decisions, risk posture, or verification expectations?
- If yes, which **specific DHF item types** are likely to change? (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `TC`, `RISK`, `RCM`, `SOUP`)
- If no, record that this is tooling/docs-only and explain why DHF impact is not expected.

Before implementation, list candidate DHF item files explicitly when DHF updates are expected.

## 5. Dependency Introduction Check

- Does the change add or materially change a Python package, GitHub Action, system tool, or external service dependency?
- If yes: why is the existing stack insufficient? What alternative was considered and rejected?
- Does this trigger a SOUP item update in the DHF?

New dependencies should not be introduced without answering these questions.

## 6. Validation Plan

- What is the narrowest meaningful test or verification command?
- Which test file covers the code being changed?
- Does the request need new tests, updated fixtures, or smoke verification?
- Read `tests/fixtures/test_data.py` and relevant doc type configs before writing new tests — field mismatches are the most common source of iteration.

## Suggested Output Format

Before implementation, state:

- intended change scope
- change class and expected gate
- product / technical fit
- expected DHF impact, including specific item types when applicable
- dependency impact if any
- planned validation commands
