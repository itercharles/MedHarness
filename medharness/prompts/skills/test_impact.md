# Test Impact

Use this guidance during CR analysis and CR design to decide the smallest sufficient
test plan for the requested change.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`, section `10. Testing Strategy`
- `DHF/documents/plans/verification_plan.md`
- `DHF/documents/plans/validation_plan.md`
- Related CRS, SYS, and SRS items identified during impact analysis

## Test Categories

- Development tests: unit/component, typecheck, lint, build, and local smoke.
  These block merge but are not compliance artifacts.
- Test-SRS: Vitest tests with `@links:SRS-xxx`; verifies software requirements.
- Test-SYS: Playwright tests with `@links:SYS-xxx`; verifies integrated system
  requirements.
- Test-CRS: Playwright workflow tests with `@links:CRS-xxx` or `UC-xxx`;
  validates user workflows.
- Manual confirmation: use only when the behavior is visual, workflow-specific,
  or clinically meaningful and cannot be fully automated yet.

## Output

Return a concise test impact entry:

```markdown
Test impact: Required | Not required | Follow-up needed
Development checks: <commands or "None beyond CI">
Verification tests: <Test-SRS/Test-SYS needs with links or "Not required">
Validation tests: <Test-CRS/UC needs with links or "Not required">
Manual confirmation: <specific check or "Not required">
```

For small UI-only changes, prefer one focused automated check plus manual visual
confirmation only when automation cannot reliably assert the result.

## Design Updates

When the approved spec requires test design changes. Prefer no change > update > create.
- Define which implementation tests must be added or updated and their expected
  `@links` annotations.
- Use Test-SRS for SRS-level unit/component behavior, Test-SYS for integrated
  system behavior, and Test-CRS for user workflow validation.
- Do not create `SWTEST` YAML unless `DHF/config/doc_types/` defines a SWTEST
  document type.
- If SWTEST item support is absent, record test requirements in the CR spec/design
  output and require implementation to add annotated tests in the product repo.
