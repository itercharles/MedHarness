# CR Design Review (Soft)

You are reviewing DHF design output that was just generated for CR {{cr_id}}.

Schema, traceability, and presence of every `affected_items` ID have already
been verified mechanically by the harness before this review runs. Your job
is the things a script cannot judge: intent, completeness, and clarity.

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Approved spec: `docs/cr-specs/{{cr_id}}-Spec.md`
- DHF changes since main: run `git diff origin/main -- DHF/`

## Review Steps

1. Read the CR item and spec to understand what was required.

2. Run `git diff origin/main -- DHF/` to see what was created or modified.

3. For each new or updated item, judge:
   - **Title and description** — does it accurately and specifically describe
     the change? Templated or generic copy is a flaw worth noting.
   - **Intent** — does the item capture what the spec actually asked for, or
     only the literal `affected_items` list? Note any items the spec narrative
     implied but did not name.
   - **Completeness** — are required content fields filled with substance,
     not placeholders?

4. Note any items the spec required that appear missing.

Do not re-verify schema, traceability links, or presence of `affected_items`
IDs — those are checked deterministically. If you spot a mechanical issue
that the deterministic check should have caught, flag it as a harness bug,
not as a design issue.

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
