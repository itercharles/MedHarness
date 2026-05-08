# CR Code Review

You are reviewing implementation code that was just generated for CR {{cr_id}}.

## Inputs

- Approved spec: `docs/cr-specs/{{cr_id}}-Spec.md`
- Code changes since main: run `git diff origin/main -- apps/ packages/` to see what was changed

## Review Steps

1. Read the approved spec to understand what was required.

2. Run `git diff origin/main -- apps/ packages/` to see the implementation.

3. Check each of the following:
   - **Completeness**: does the code implement everything the spec describes?
   - **Tests**: are there colocated tests (`*.test.ts(x)`) for every functional change?
   - **Annotations**: do tests that cover DHF requirements have `@links:SRS-xxx` or
     `@links:SYS-xxx` annotations?
   - **Types**: TypeScript strict mode respected? No `any` types?
   - **Styling**: Tailwind only, no inline styles?
   - **Scope**: no unrelated refactoring or speculative additions beyond the spec?
   - **Shared types**: new types defined in `packages/shared-types` before use in apps?

## Output

Write the review to `docs/cr-specs/{{cr_id}}-Code-Review.md`:

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
