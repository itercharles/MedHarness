# Risk Impact

Use this guidance during CR analysis and CR design for clinical workflow, DICOM,
contouring, review, dose, repository, security, data integrity, or user action
changes.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/risk_management_plan.md`
- Risk items (see Type Registry — `risk` role)
- Risk control items (see Type Registry — `risk_control` role)
- Related system and software requirement items when applicable

## Analysis

Check whether the CR:
- Introduces a new hazard, hazardous situation, or foreseeable misuse.
- Changes an existing risk control or makes a control less visible/effective.
- Changes clinical data integrity, patient selection, RTSTRUCT handling, image
  display, contour editing, dose, QA, or repository exchange behavior.
- Requires new risk items, new risk controls, or updates to existing items.

## Output

Return a concise risk impact entry:

```markdown
Risk / Risk Controls: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <risk / risk control item IDs or "None">
Recommended action: <none, update risk items, or create risk items during design>
```

For purely cosmetic or non-functional removals, use `Not required` only when no
clinical workflow, safety control, or data integrity behavior changes.

## Design Updates

When the approved spec requires risk changes. Prefer no change > update > create.
- Update or create **risk items** (see Type Registry — `risk` role).
- Update or create **risk control items** (see Type Registry — `risk_control` role).
- Link risk controls to risk items through `mitigates`.
- Link implemented controls to system requirements (tier-2) where applicable.
- Keep risk updates focused on hazards, harms, causes, controls, and residual
  risk; do not duplicate requirements text.
