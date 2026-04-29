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

| Class | Gate | DHF impact |
|---|---|---|
| `docs/process` | Doc consistency check | None expected — state explicitly if so |
| `infra/devops` | Validation + rollback plan | `SOUP` if new dependency; otherwise none |
| `bugfix` | Regression test, CR required | `TC` if test added/updated; `SRS`/`SYS` if documented behavior corrected; `RISK`/`RCM` if safety-relevant |
| `feature` | Branch, PR, CR required | `UC`/`CRS` (user-facing); `SYS`/`SRS` (system/software behavior); `SWDD` (design detail); `TC` (tests); `RISK`/`RCM` (risk posture); `SOUP` (new library) |
| `architecture` | Branch, PR, CR required | `SYSARCH` (always); `SYS`/`SRS` if requirements change; `SWDD`; `RISK`/`RCM` if risk posture changes; `SOUP` if new dependency |

## 2. Product Direction Check

- Is the request consistent with [`docs/product_strategy.md`](../docs/product_strategy.md)?
- Is it aligned with the current milestone in [`docs/product_roadmap.md`](../docs/product_roadmap.md)?
- Does it strengthen CompliantFlow's core value (compliance gate, DHF template, AI harness) or is it pulling in scope that doesn't fit the current phase?
- Should the request be narrowed because it conflicts with current focus?

If the request conflicts with product direction, state the conflict before implementation.

## 3. Technical Direction Check

- Is the request consistent with [`docs/technical_strategy.md`](../docs/technical_strategy.md)?
- Does it preserve the adapter boundary (product repos call CompliantFlow/DHF facade APIs, not DHF storage paths)?
- Does it preserve the product/DHF repo separation?
- Does it add infrastructure or abstractions that will be hard to validate or maintain?
- Does it introduce assumptions about local paths, user environment, or external services?

If the request conflicts with technical direction, state the conflict before implementation.

## 4. DHF Impact Check

Use the table in section 1 to determine expected DHF item types for the change class. Then confirm:

- Will this request modify product behavior, requirements, architecture decisions, risk posture, or verification expectations?
- If yes, which **specific DHF item files** in `compliantflow-dhf/DHF/items/` are affected?
- If no, state explicitly that this is tooling/docs-only and explain why DHF impact is not expected.

List candidate DHF item files before writing any code.

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
