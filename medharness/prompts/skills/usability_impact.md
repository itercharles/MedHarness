# Usability / HFE Impact

Use this guidance during CR analysis and CR design when a change may affect user
interaction, workflow, error prevention, or the usability engineering file per
IEC 62366-1 and FDA guidance on Human Factors Engineering.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- `DHF/documents/plans/usability_engineering_plan.md` (if present)
- Risk items and use case / customer requirement items identified during impact
  analysis (see Type Registry for type codes)

## Analysis

Check whether the CR:
- Changes user-facing UI, interaction patterns, navigation, or workflow
  sequences.
- Introduces new user tasks, roles, or permissions that alter how users
  interact with the system.
- Modifies error messages, alerts, confirmations, or undo capabilities that
  affect use error prevention.
- Changes the visibility, accessibility, or discoverability of safety-critical
  controls or information.
- Introduces new display modalities, input methods, or assistive technology
  interactions.
- Alters the user's mental model of system behavior (e.g., changing what a
  button does, reordering steps in a clinical workflow).
- Triggers formative or summative usability evaluation per the usability
  engineering plan.
- Requires updates to the HFE/Usability Engineering File.

## Output

Return a concise usability impact entry:

```markdown
Usability / HFE: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <use case / risk item IDs or "None">
Recommended action: <none, flag for formative eval, schedule summative test,
  update HFE file, or consult usability during design>
```

For back-end, infrastructure, or non-user-facing changes, use `Not required`.
For small UI-adjustment changes (copy, spacing, color) that do not alter
interaction flow, use `Not required` when no new use error hazard is introduced.

## Design Updates

When the approved spec requires usability changes. Prefer no change > update > create.
- Update or create **use case items** for changed or new user workflows (see
  Type Registry — `use_case` role).
- Update **risk items** when use-related hazards are introduced or changed (see
  Type Registry — `risk` role).
- Do not create standalone HFE DHF items unless the project config defines
  a usability document type.
- Flag items that require usability review before approval so the reviewer
  gate can surface them.
