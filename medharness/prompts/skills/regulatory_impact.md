# Regulatory Impact

Use this guidance during CR analysis and CR design when a change may affect
regulatory submissions, product classification, labeling, or compliance with
medical device regulations (21 CFR 820.30, MDR Annex IX, ISO 13485).

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- `DHF/documents/plans/regulatory_strategy_plan.md` (if present)
- Related system requirements, risk items, and SOUP items identified during
  impact analysis (see Type Registry for type codes)

## Analysis

Check whether the CR:
- Changes the intended use, indications for use, or patient population.
- Adds, removes, or materially alters a safety-critical feature.
- Modifies clinical workflow, decision support, or diagnostic output.
- Introduces a new external interface, data exchange format, or interoperability
  claim that affects the device classification boundary.
- Triggers a 510(k) premarket notification, Special 510(k), MDR significant
  change, or other regulatory filing in applicable jurisdictions.
- Requires updates to Instructions for Use (IFU), labeling, patient-facing
  materials, or training requirements.
- Changes the UDI or device identifier content.
- Affects predicate device comparison or substantial equivalence arguments.

## Output

Return a concise regulatory impact entry:

```markdown
Regulatory: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <DHF item IDs or "None">
Recommended action: <none, update regulatory plan, flag for 510(k) review,
  update IFU/labeling, or consult regulatory during design>
```

For cosmetic, localization, or non-functional documentation changes, use
`Not required` when no regulatory filing, labeling, or classification impact
exists.

## Design Updates

When the approved spec requires regulatory changes. Prefer no change > update > create.
- Note regulatory filing triggers in the CR design output; do not create DHF
  items for external regulatory submissions.
- Update IFU or labeling content in `DHF/documents/` when scope requires it.
- Flag items that require regulatory review before approval so the reviewer
  gate can surface them.
- Do not invent 510(k) conclusions — flag for follow-up when the determination
  requires regulatory specialist input.
