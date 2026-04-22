# Post-Implement Checklist

Review this checklist after implementation and before handoff.

## 1. Scope Review

- Was the implemented change actually limited to the agreed request?
- Did the change introduce unrelated behavior or cleanup?
- Were any hidden assumptions added that should be documented?
- Was the final change still consistent with the original change class?

## 2. Direction Review

- Does the final implementation still align with the two-CLI split (`compliantflow/` read-only, DHF mutations via `python -m utils`)?
- Does it still preserve the product/DHF repo separation?
- If the implementation diverged from the original plan, is that divergence justified?

## 3. DHF Review

- Were DHF items updated when they should have been?
- If DHF was not updated, is the reason explicit?
- List the exact DHF item files changed, or state clearly that no DHF update was required.

## 4. Dependency Review

- Was a new Python package, GitHub Action, system tool, or external service introduced?
- If yes: was the rationale, rejected alternative, and SOUP/DHF impact made explicit?

## 5. Verification Review

- Which commands were actually run?
- Did all tests pass?
- Was any smoke verification run?
- What was not verified?

Do not claim validation without naming the commands. Use `.venv/bin/python -m pytest <file> -q`.

## 6. Delivery Review

- Does this change modify product behavior, CLI output, compliance logic, or the dhf-template?
- If yes, was the work done on a dedicated branch?
- Is a PR required before merge?
- Does the PR description include:
  - a concise summary
  - the exact DHF files changed, or a statement that no DHF update was needed
  - the validation commands actually run
  - manual testing still required, with concrete steps
- After PR creation, is there a follow-up plan to monitor CI and review comments?
- If review comments exist, has each been triaged into: fix now / do not fix (with rationale) / ask for clarification / defer?

## 7. Residual Risk Review

- For CI/CD changes: what is the rollback path?
- For init/template changes: where would a user look first if the generated output is wrong?
- What remains risky, incomplete, or requires manual verification?
- Are there follow-up items to carry into the next task?

## 8. Definition Of Done Check

Work is only complete when:

- [ ] scope stayed aligned with the agreed request
- [ ] two-CLI split and product/DHF separation were preserved
- [ ] DHF impact was assessed and documented (files listed or explicitly none)
- [ ] dependency impact was assessed and documented
- [ ] relevant tests were run and named
- [ ] branch / PR requirements were met when applicable
- [ ] remaining manual testing is explicit
- [ ] residual risks are explicit

## Suggested Output Format

Before final handoff, state:

- what changed
- change class
- which DHF files changed (or: no DHF update required)
- which tests / verification commands were run
- whether a branch / PR was created
- what manual testing is still required
- remaining risks or follow-up items
