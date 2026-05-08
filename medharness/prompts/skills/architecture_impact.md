# Architecture Impact

Use this guidance during CR analysis and CR design when a change may affect WebTPS
architecture, system boundaries, data flow, deployment topology, repository
integration, or shared contracts.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/development_plan.md`
- `DHF/items/06_sys_arch/`
- `DHF/documents/specs/architecture_specification.md.j2`
- Relevant SYS/SRS items when the CR references them

## Analysis

Check whether the CR changes:
- Client/API/shared-types boundaries.
- DICOM repository integration or repository-first data flow.
- Long-running or server-side orchestration responsibility.
- Deployment, CI, local setup, or operational architecture.
- Architecture traceability from `SYSARCH` to `SYS`.

## Output

Return a concise architecture impact entry:

```markdown
Architecture / SYSARCH: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <SYSARCH IDs or "None">
Recommended action: <none, update SYSARCH, update architecture spec, or create SYSARCH during design>
```

Do not require architecture updates for localized UI copy, icon, or visibility
changes that do not alter system boundaries or data flow.

## Design Updates

When the approved spec requires architecture changes. Prefer no change > update > create.
- Update or create `SYSARCH` items under `DHF/items/06_sys_arch/`.
- Link SYSARCH items to affected `SYS` requirements through `design`.
- Update architecture specification source content only when architecture
  narrative, boundaries, data flow, deployment, or integration assumptions change.
- Do not use SYSARCH for implementation details that belong in SRS or SWDD.
