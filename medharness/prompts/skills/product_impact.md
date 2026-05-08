# Product Impact

Use this guidance during CR analysis and CR design before deciding whether DHF
product items need updates.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- `DHF/items/00_uc/`
- `DHF/items/01_req_crs/`

## Analysis

Check:
- Whether the request fits the current development phase and product direction.
- Whether existing UC items already cover the user workflow.
- Whether existing CRS items already cover the user-facing need.
- Whether the request introduces a new user workflow, changes a clinical workflow,
  changes user-visible behavior, or only corrects implementation/UI drift.

## Output

Return a concise product impact entry:

```markdown
Product / UC / CRS: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <UC/CRS IDs or "None">
Recommended action: <none, update UC/CRS, or create UC/CRS during design>
```

For small UI removals or wording fixes, prefer `Not required` when existing UC/CRS
coverage remains accurate.

## Design Updates

When the approved spec requires product item changes. Prefer no change > update > create.
- Update or create `UC` items for new or changed user workflows.
- Update or create `CRS` items for user-facing needs and stakeholder value.
- Keep CRS linked to UC through `derives_from`.
- Do not create SYS or SRS items here; use the req-manage guidance for those.
