# CR Analysis Task

You are working in the DHF repository for WebTPS. Your task is to produce
a concise technical implementation spec for the CR listed below.

CR ID: {{cr_id}}

## Inputs

Read these files:
- `DHF/items/09_cr/{{cr_id}}.yaml` — the CR definition
- `CLAUDE.md` — repository conventions and toolchain
- `README.md` — project overview
- `docs/cr_spec_workflow.md` — CR and spec ownership model

## Steps

1. Read the CR item and repository context files listed above.

2. Before writing `affected_items`, enumerate all valid DHF item IDs:

       python -m medharness --dhf DHF dhf item list

   This prints one JSON object per line. Each object has `"id"`, `"type"`,
   `"title"`. Only reference `id` values from this output in `affected_items`.

3. Apply the DHF impact skills (provided below) to determine which DHF areas
   are affected. For each area state: `Required`, `Not required`, or
   `Follow-up needed` with a one-sentence justification.

4. For each required item type (SYS, SRS, SWDD, RISK, etc.), enumerate the
   existing items of that type and identify:
   - Which existing items are touched or need updating
   - What new items need to be created, with their proposed title and content

   Document this in the DHF Impact section of the spec so the design phase
   can act on it directly. Do not create or modify any DHF items — analysis only.

5. If the runtime provides `$DHF_CONTEXT.test_coverage.manual_verification_candidates`,
   use those item IDs as the starting point for `test_plan.must_be_manual`
   instead of guessing. Keep `auto_covered`, `needs_new_tc`, and
   `must_be_manual` aligned with the machine-readable coverage hints when they
   are present.

6. Produce the spec at `docs/cr-specs/{{cr_id}}-Spec.md`.
   Keep it short. Do not enumerate hundreds of speculative risks or test cases.

7. Do not modify any file other than `docs/cr-specs/{{cr_id}}-Spec.md`.

## Spec Format

The spec MUST begin with this YAML front-matter (machine-read by CI):

```
---
cr_id: "{{cr_id}}"
direction_fit: in-scope        # one of: in-scope | scope-expansion | out-of-scope
affected_items:                # existing DHF item IDs this CR touches; [] if none
  - SYS-001
proposed_new_items:            # DHF items to create in the design stage; [] if none
  - type: SRS
    title: "Example new requirement title"
design_impact_summary: "..."   # 1-2 sentences summarizing overall design impact
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
