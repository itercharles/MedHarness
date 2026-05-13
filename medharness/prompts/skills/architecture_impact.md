# Architecture Impact

Use this guidance during CR analysis and CR design when a change may affect the
system architecture, system boundaries, data flow, deployment topology, or
shared contracts.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- Architecture items (see Type Registry — `architecture` role)
- `DHF/documents/specs/architecture_specification.md.j2`
- Relevant system requirement and software requirement items when the CR references them

## Analysis

Check whether the CR changes:
- Client/API/shared-types boundaries.
- DICOM repository integration or repository-first data flow.
- Long-running or server-side orchestration responsibility.
- Deployment, CI, local setup, or operational architecture.
- Architecture traceability from architecture items to system requirements.

## Output

Return a concise architecture impact entry:

```markdown
Architecture: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <architecture item IDs or "None">
Recommended action: <none, update architecture items, update architecture spec,
  or create architecture items during design>
```

Do not require architecture updates for localized UI copy, icon, or visibility
changes that do not alter system boundaries or data flow.

## Design Updates

When the approved spec requires architecture changes. Prefer no change > update > create.
- Update or create **architecture items** (see Type Registry — `architecture` role).
- Link architecture items to affected system requirements (tier-2) through `design`.
- Update architecture specification source content only when architecture
  narrative, boundaries, data flow, deployment, or integration assumptions change.
- Do not use architecture items for implementation details that belong in
  tier-3 or tier-4 items.
