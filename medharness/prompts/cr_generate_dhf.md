# CR DHF Generation Task (V-Model Cascade)

You are working in the DHF repository. Given a single CR, your task is to generate
the **complete DHF item cascade** in one session, reasoning top-down through the
V-model hierarchy and writing items via the medharness CLI.

CR ID: {{cr_id}}

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Repository context: `CLAUDE.md`, `README.md`

Read these files first.

## V-Model Generation Order

The V-model is your **reasoning framework**, not a sequential execution plan.
Reason top-down to understand requirements; create items in this order so
traceability links can reference already-created items:

CR (input -- do not modify)
 └─► CRS   (satisfies UC -- link derives_from UC if one exists)
      └─► SYS   (satisfies CRS -- link satisfies to CRS IDs)
          ├─► SYSARCH  (designs SYS -- link design to SYS IDs)
          ├─► RISK     (hazards arising from SYS)
          ├─► RCM      (mitigates RISK, implements SYS)
          └─► SRS   (derives_from SYS, constrained by RCM where applicable)
               └─► SWDD  (implements SRS -- link implements to SRS IDs)

Before writing any items, enumerate existing items for each type you plan to touch:

    python -m medharness --dhf DHF dhf item list --type <TYPE>

Apply the change preference: **no change > update existing > create new**.
Only create a new item when no existing item covers the need.

## verification_criteria Field (CRS, SYS, SRS only)

For every CRS, SYS, and SRS item you create or update, populate the
`verification_criteria` field with a concise, **measurable** criterion:

- State observable outcomes, thresholds, or pass/fail conditions.
- Avoid vague language ("works correctly", "behaves as expected").
- Example: "The system shall authenticate users within 2 seconds at the 95th
  percentile under nominal load conditions."

Do **not** invent TC item IDs or create TC items. TC IDs are derived by naming
convention from requirement IDs (TC-SYS-001-001 from SYS-001, TC-SRS-003-001
from SRS-003). Tests link back via `medharness.links` in JUnit -- no links in
DHF item YAML are needed.

SWDD, RISK, and RCM items do **not** need `verification_criteria` -- omit it.

If you are updating an existing CRS/SYS/SRS and `verification_criteria` is
absent or vague, add or improve it.

## CLI Commands

**Create a new item (ID assigned automatically by medharness):**

    python -m medharness --dhf DHF dhf item create \
      --type <TYPE> --data '<JSON>' \
      --author "github-actions[bot]" --cr "{{cr_id}}"

**Update an existing item:**

    python -m medharness --dhf DHF dhf item update <ITEM_ID> \
      --data '<JSON>' \
      --author "github-actions[bot]" --cr "{{cr_id}}"

**List items for context:**

    python -m medharness --dhf DHF dhf item list --type <TYPE>
    python -m medharness --dhf DHF dhf item list

Do **not** write YAML files directly. Do **not** modify the CR item itself.

## Inline Validation Hook

After writing all items, validate and self-correct before finishing:

    python -m medharness --dhf DHF dhf validate schema
    python -m medharness --dhf DHF dhf validate traceability

If either reports errors introduced by your changes, fix them via `dhf item update`
and re-validate. Repeat until both pass cleanly.

## Scope Constraints

- Only create or update items **directly required** by this CR.
- Do not create items for hypothetical future changes.
- Do not modify files outside `DHF/`.
- Do not edit CR lifecycle or status fields.

## DHF Impact Skills
