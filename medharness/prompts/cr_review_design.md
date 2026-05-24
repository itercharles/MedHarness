# CR Design Review (Soft)

You are reviewing DHF items that were just generated for CR {{cr_id}}.

Schema validity and traceability links have already been verified mechanically
by the harness before this review runs. Your job is the things a script cannot
judge: whether every item is necessary, whether the design fits the product and
technical strategy, and whether SWDD items and implementation notes are clear
enough to hand off to a developer.

## Inputs

- CR item: run `dhfkit --dhf DHF item get {{cr_id}}`
- Items changed in this session:

      git diff --name-only origin/main -- DHF/

Read each changed item in full.

## Review Steps

1. Read the CR item to understand what was requested and why.

2. List changed DHF items:

       git diff --name-only origin/main -- DHF/

3. Read each changed item.

4. Judge each item on three questions:

   **Necessity** — Is this item directly required by the CR, or is it speculative,
   premature, or out of scope? Every created item must trace to a concrete requirement
   in the CR or an upstream item. Every updated item must reflect a change the CR
   actually demands.

   **Strategy alignment** — Does this item fit the product direction and technical
   strategy described in `CLAUDE.md` and any existing SYSARCH or ADR items? Flag
   anything that contradicts stated direction or introduces architectural drift.

   **SWDD and implementation note clarity** — For SWDD items: is the design decision
   clearly stated? Would a competent developer know what to build without re-reading
   source code or re-deriving design choices from the SRS? For the `implementation_notes`
   field on the CR item: are the steps concrete, ordered, and complete enough to
   implement without additional context?

Do not re-verify schema or traceability links — those are checked deterministically.
If you spot a mechanical issue the deterministic check should have caught, flag it
as a harness bug, not a design issue.

## Output

Write the review to `docs/reviews/{{cr_id}}-Design-Review.md`:

```markdown
# Design Review: {{cr_id}}

**Verdict:** Approved | Needs Revision

## Summary
<one paragraph>

## Issues
- [ ] `<item_id>`: <what is wrong and what change is needed>
```

If no issues are found, write `No issues found.` under Issues.

Do not modify any DHF item files — this is a review pass only.
