# CR Design Review

You are reviewing DHF design output that was just generated for CR {{cr_id}}.

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Approved spec: `docs/cr-specs/{{cr_id}}-Spec.md`
- DHF changes since main: run `git diff origin/main -- DHF/` to see what was created or modified

## Review Steps

1. Read the CR item and the spec to understand what was required.

2. Run `git diff origin/main -- DHF/` to see which items were created or updated.

3. For each item listed in `affected_items` in the spec front-matter, verify:
   - Was the item created or updated?
   - Is the title and description accurate and complete?
   - Are `dhf_links` correct (traceability: UC → CRS → SYS → SRS → SWDD)?
   - Are all required fields present?

4. Check for missing items: anything the spec required that was not created.

5. Check for incorrect traceability: items linked to the wrong parents or missing links.

## Output

Write the review to `docs/cr-specs/{{cr_id}}-Design-Review.md`:

```markdown
# Design Review: {{cr_id}}

**Verdict:** Approved | Needs Revision

## Summary
<one paragraph>

## Issues
- [ ] <item-id>: <what is wrong and what fix is needed>
```

If no issues are found, write `No issues found.` under Issues.

Do not modify any DHF items — this is a review pass only.
