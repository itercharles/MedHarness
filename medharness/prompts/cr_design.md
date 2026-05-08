# CR Design Task

You are working in the DHF repository for WebTPS.

CR ID: {{cr_id}}

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Spec: `docs/cr-specs/{{cr_id}}-Spec.md`
- Repository context: `CLAUDE.md`, `README.md`, and `docs/cr_spec_workflow.md`

## Steps

1. Read the CR item, the approved spec, and the repository context.

2. For each DHF item type you plan to touch, enumerate existing items first:

       python -m medharness --dhf DHF dhf item list --type <TYPE>

   Use this to detect conflicts and duplicates before writing anything.

3. Create or update DHF items exclusively through the medharness CLI —
   do NOT write YAML files directly:

   ```
   # Create
   python -m medharness --dhf DHF dhf item create \
     --type <TYPE> --data '<JSON>' --author "github-actions[bot]" --cr "{{cr_id}}"

   # Update
   python -m medharness --dhf DHF dhf item update <ITEM_ID> \
     --data '<JSON>' --author "github-actions[bot]" --cr "{{cr_id}}"
   ```

   IDs are assigned by medharness on creation.

4. If the CR calls for specification documents, create or update them under
   `DHF/documents/specs/` or `DHF/documents/plans/` (direct file writes are
   permitted for documents, not for DHF items).

5. After all items are written, validate schema and traceability:

       python -m medharness --dhf DHF dhf validate schema
       python -m medharness --dhf DHF dhf validate traceability

   If either reports errors introduced by your changes, fix them and
   re-validate. Repeat until both pass.

6. Do not modify files outside `DHF/`.
7. Do not edit the CR item YAML or any CR lifecycle/status fields.

## DHF Impact Skills

Apply the impact guidance below to decide which areas need updates and how to
structure the new or modified DHF items.
