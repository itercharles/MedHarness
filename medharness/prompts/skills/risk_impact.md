# Risk Impact

Use this guidance during CR analysis and CR design for clinical workflow, DICOM,
contouring, review, dose, repository, security, data integrity, or user action
changes.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/risk_management_plan.md`
- `DHF/items/12_risks/`
- `DHF/items/13_rcm/`
- Related SYS/SRS items when applicable

## Analysis

Check whether the CR:
- Introduces a new hazard, hazardous situation, or foreseeable misuse.
- Changes an existing risk control or makes a control less visible/effective.
- Changes clinical data integrity, patient selection, RTSTRUCT handling, image
  display, contour editing, dose, QA, or repository exchange behavior.
- Requires new `RISK` or `RCM` items, or updates to existing items.

## Output

Return a concise risk impact entry:

```markdown
Risk / RCM: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <RISK/RCM IDs or "None">
Recommended action: <none, update RISK/RCM, or create RISK/RCM during design>
```

For purely cosmetic or non-functional removals, use `Not required` only when no
clinical workflow, safety control, or data integrity behavior changes.

## Design Updates

When the approved spec requires risk changes. Prefer no change > update > create.
- Update or create `RISK` items under `DHF/items/12_risks/`.
- Update or create `RCM` items under `DHF/items/13_rcm/`.
- Link `RCM.mitigates` to `RISK` items.
- Link implemented controls to `SYS` requirements where applicable.
- Keep risk updates focused on hazards, harms, causes, controls, and residual
  risk; do not duplicate requirements text.
