# Product Impact

Use this guidance during CR analysis and CR design before deciding whether DHF
product items need updates.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- Use case and customer requirement items (tier-0 and tier-1 types — see Type Registry)

## Analysis

Check:
- Whether the request fits the current development phase and product direction.
- Whether existing use case items already cover the user workflow.
- Whether existing customer requirement items already cover the user-facing need.
- Whether the request introduces a new user workflow, changes a clinical workflow,
  changes user-visible behavior, or only corrects implementation/UI drift.

## Output

Return a concise product impact entry:

```markdown
Product / User needs: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <tier-0 / tier-1 item IDs or "None">
Recommended action: <none, update existing items, or create new items during design>
```

For small UI removals or wording fixes, prefer `Not required` when existing
use case and customer requirement coverage remains accurate.

## Design Updates

When the approved spec requires product item changes. Prefer no change > update > create.
- Update or create **use case items** (tier-0 — see Type Registry) for new or
  changed user workflows.
- Update or create **customer requirement items** (tier-1 — see Type Registry)
  for user-facing needs and stakeholder value.
- Keep tier-1 items linked to tier-0 items through `derives_from`.
- Do not create tier-2 or lower items here; use the req-manage guidance for those.
