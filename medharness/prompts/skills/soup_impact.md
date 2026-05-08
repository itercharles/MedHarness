# SOUP Impact

Use this guidance during CR analysis and CR design when a change may add, remove,
upgrade, replace, or materially change the use of third-party software.

## Inputs

Read:
- `DHF/items/09_cr/<CR_ID>.yaml`
- `DHF/documents/plans/configuration_management_plan.md`
- `DHF/documents/plans/maintenance_plan.md`
- `DHF/items/11_soup/`
- Product dependency manifests if relevant

## Analysis

Check whether the CR:
- Adds, removes, upgrades, or replaces a runtime, build, test, AI, DICOM, UI, or
  infrastructure dependency.
- Changes the safety purpose or operating context of an existing SOUP item.
- Requires SOUP version, license, manufacturer, CVE, risk rating, or verification
  method updates.
- Requires affected SRS items to reference SOUP usage.

## Output

Return a concise SOUP impact entry:

```markdown
SOUP / Dependencies: Required | Not required | Follow-up needed
Justification: <one sentence>
Impacted items: <SOUP IDs or "None">
Recommended action: <none, update SOUP, create SOUP, or inspect manifests during implementation>
```

Do not require SOUP updates for changes that only use existing dependencies in
the same approved way.

## Design Updates

When the approved spec requires SOUP changes. Prefer no change > update > create.
- Update or create `SOUP` items under `DHF/items/11_soup/`.
- Record name, version, manufacturer, license, purpose, homepage, risk rating,
  safety class, and verification method when known.
- If dependency details are not available during design, mark the item or spec
  as follow-up for implementation rather than inventing values.
- Ensure affected SRS items reference SOUP usage if the repository schema supports
  that relationship.
