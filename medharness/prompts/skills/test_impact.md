# Test Impact

Use this guidance during CR analysis and CR design to decide the smallest sufficient
test plan for the requested change.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`, section `10. Testing Strategy`
- `DHF/documents/plans/verification_plan.md`
- `DHF/documents/plans/validation_plan.md`
- Requirement items identified during impact analysis (all tiers — see Type Registry)

## Test Categories

- **Development tests**: unit/component, typecheck, lint, build, and local smoke.
  These block merge but are not compliance artifacts.
- **Verification tests** (tier-2 / tier-3 requirements): automated tests that
  verify system or software requirements. Link to the requirement item IDs they
  cover using `@links:<ITEM_ID>` annotations in the test file.
- **Validation tests** (tier-0 / tier-1 requirements): automated or manual tests
  that validate user workflows against use case and customer requirement items.
  Link using `@links:<ITEM_ID>` annotations.
- **Manual confirmation**: use only when the behavior is visual, workflow-specific,
  or clinically meaningful and cannot be fully automated.

The `@links:` annotation uses the actual item ID from the spec — for example
`@links:SYS-012` in a project that uses SYS as the system requirement type, or
`@links:SYSREQ-012` in a project that uses SYSREQ. Resolve the correct prefix
from the **Type Registry**.

## Output

Return a concise test impact entry:

```markdown
Test impact: Required | Not required | Follow-up needed
Development checks: <commands or "None beyond CI">
Verification tests: <requirement IDs needing new automated tests, or "Not required">
Validation tests: <use case / customer requirement IDs needing coverage, or "Not required">
Manual confirmation: <specific check or "Not required">
```

For small UI-only changes, prefer one focused automated check plus manual visual
confirmation only when automation cannot reliably assert the result.

## Design Updates

When the approved spec requires test design changes. Prefer no change > update > create.
- Define which implementation tests must be added or updated and their expected
  `@links:<ITEM_ID>` annotations, using the item IDs from the approved spec.
- Use verification tests for tier-2/tier-3 requirement coverage and validation
  tests for tier-0/tier-1 workflow coverage.
- Do not create test document type YAML items unless the project's DHF config
  defines a test document type. If absent, record test requirements in the CR
  spec/design output and require implementation to add annotated tests in the
  product repo.
