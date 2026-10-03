# CR Code Review (Soft)

You are reviewing implementation code that was just generated for CR {{cr_id}}.

Requirement-to-test coverage has already been verified mechanically by the
harness before this review runs. Your job is the things a script cannot judge:
completeness against the CR and its `implementation_notes`, test depth, and code
quality.

## Inputs

- CR item: run `medharness --dhf DHF item get {{cr_id}}`
- Code changes since main: run `git diff origin/main -- . ':(exclude)DHF' ':(exclude)docs/reviews'`

## Review Steps

1. Read the CR item (`medharness --dhf DHF item get {{cr_id}}`) to understand what was required.

2. Run `git diff origin/main -- . ':(exclude)DHF' ':(exclude)docs/reviews'` to see the implementation.

3. Judge:
   - **Completeness** — does the code implement everything the CR and its
     `implementation_notes` call for?
   - **Test depth** — beyond the annotated tests, does coverage match the
     surface area of the change? Are edge cases addressed, not just the
     happy path?
   - **Scope** — any unrelated refactoring, dead code, or speculative
     additions outside what the CR describes?
   - **Conventions** — Read `AGENTS.md`/`CLAUDE.md` for this project's coding
     conventions, then check the
     implementation against them. If no conventions are documented, limit
     your review to correctness, test depth, completeness, and scope —
     do not import conventions from other projects.

Do not re-verify the presence of `@links:` annotations — requirement coverage is
checked deterministically. If you spot a mechanical issue that the deterministic
check should have caught, flag it as a harness bug, not as a code issue.

## Output

Respond with the review in this exact format — do not write any files:

```
# Code Review: {{cr_id}}

**Verdict:** Approved | Needs Revision

## Summary
<one paragraph>

## Issues
- [ ] `<file>:<line>`: <what is wrong and what fix is needed>
```

If no issues are found, write `No issues found.` under Issues.

Do not modify any code files — this is a review pass only.
