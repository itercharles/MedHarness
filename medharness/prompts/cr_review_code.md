# CR Code Review (Soft)

You are reviewing implementation code that was just generated for CR {{cr_id}}.

Test annotations for item-ID entries in the spec's `test_plan.needs_new_tc`
have already been verified mechanically by the harness before this review runs.
Your job is the things a script cannot judge: completeness against the spec
narrative, test depth, and code quality.

## Inputs

- CR item: run `medharness --dhf DHF dhf item get {{cr_id}}`
- Code changes since main: run `git diff origin/main -- apps/ packages/`

## Review Steps

1. Read the CR item (`medharness --dhf DHF dhf item get {{cr_id}}`) to understand what was required.

2. Run `git diff origin/main -- apps/ packages/` to see the implementation.

3. Judge:
   - **Completeness** — does the code implement the full spec, including
     anything described in the narrative beyond the explicit checklist?
   - **Test depth** — beyond the annotated tests, does coverage match the
     surface area of the change? Are edge cases addressed, not just the
     happy path?
   - **Scope** — any unrelated refactoring, dead code, or speculative
     additions outside what the spec describes?
   - **Conventions** — TypeScript strict (no `any`), Tailwind only (no
     inline styles), shared types defined in `packages/shared-types`
     before use in apps.

Do not re-verify the presence of `@links:` annotations for item-ID entries in
`test_plan.needs_new_tc` — those are checked deterministically. If you
spot a mechanical issue that the deterministic check should have caught,
flag it as a harness bug, not as a code issue.

## Output

Write the review to `docs/reviews/{{cr_id}}-Code-Review.md`:

```markdown
# Code Review: {{cr_id}}

**Verdict:** Approved | Needs Revision

## Summary
<one paragraph>

## Issues
- [ ] `<file>:<line>`: <what is wrong and what fix is needed>
```

If no issues are found, write `No issues found.` under Issues.

Do not modify any code files — this is a review pass only.
