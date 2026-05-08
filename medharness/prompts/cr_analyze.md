# CR Analysis Task

You are working in the DHF repository for WebTPS. Your task is to produce
a concise technical implementation spec for the CR listed below, and to
create or update the DHF requirement items (SYS, SRS, SWDD) it introduces.

CR ID: {{cr_id}}

## Inputs

Read these files:
- `DHF/items/09_cr/{{cr_id}}.yaml` — the CR definition
- `CLAUDE.md` — repository conventions and toolchain
- `README.md` — project overview
- `docs/cr_spec_workflow.md` — CR and spec ownership model

## Steps

1. Read the CR item and repository context files listed above.

2. Enumerate existing DHF items before writing anything:

       python -m medharness --dhf DHF dhf item list

   This prints one JSON object per line. Each object has `"id"`, `"type"`,
   `"title"`. Check for existing items that may already cover the CR's
   requirements — update rather than duplicate.

3. Apply the DHF impact skills (provided below) to determine which DHF areas
   are affected. For each area state: `Required`, `Not required`, or
   `Follow-up needed` with a one-sentence justification.

4. Create or update DHF requirement items via the medharness CLI — do NOT
   write YAML files directly. Work top-down: SYS → SRS → SWDD.

   Only create items when the CR introduces requirements not already covered
   by existing items. Follow the traceability rules in the Requirements
   Management skill below.

   ```bash
   # Create
   python -m medharness --dhf DHF dhf item create \
     --type <TYPE> --data '<JSON>' --author "github-actions[bot]" --cr "{{cr_id}}"

   # Update
   python -m medharness --dhf DHF dhf item update <ITEM_ID> \
     --data '<JSON>' --author "github-actions[bot]" --cr "{{cr_id}}"
   ```

   IDs are assigned by medharness on creation — capture them for use in
   `affected_items` and as link targets for lower-level items.

5. Validate schema and traceability; fix any errors and re-validate.

       python -m medharness --dhf DHF dhf validate schema
       python -m medharness --dhf DHF dhf validate traceability

6. Produce the spec at `docs/cr-specs/{{cr_id}}-Spec.md`.
   Keep it short. Do not enumerate hundreds of speculative risks or test cases.
   In `affected_items`, list all DHF item IDs you created or updated in step 4,
   plus any pre-existing items you determined are touched by this CR.

7. Do not edit `DHF/items/09_cr/{{cr_id}}.yaml` or any CR lifecycle fields.

## Spec Format

The spec MUST begin with this YAML front-matter (machine-read by CI):

```
---
cr_id: "{{cr_id}}"
direction_fit: in-scope        # one of: in-scope | scope-expansion | out-of-scope
affected_items:                # DHF item IDs created or touched by this CR; [] if none
  - SYS-001
test_plan:
  auto_covered:                # items covered by existing automated tests
    - SRS-001
  needs_new_tc:                # items requiring new test cases
    - SRS-002
  must_be_manual:              # items only verifiable manually
    []
---
```

`direction_fit`:
- `in-scope` — fits current roadmap without extending scope
- `scope-expansion` — adds capability beyond current roadmap
- `out-of-scope` — conflicts with or is outside product strategy

Markdown sections after the front-matter:
1. Summary
2. Implementation Plan
3. DHF Impact
4. Verification
5. Implementation Checklist
6. Open Questions
