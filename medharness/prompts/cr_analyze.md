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
   - When you can determine the direct DHF parent for a proposed new item,
     include it as `parent` (for example `SYS-001` for a new `SRS` item)
   - When the CR makes the verification approach clear, include
     `verification_method` as one of `Test`, `Inspection`, `Analysis`, or
     `Demonstration`, but only for proposed item types whose schema supports
     that field today (`SYS` and `SOUP`)

   Document this in the DHF Impact section of the spec so the design phase
   can act on it directly. Do not create or modify any DHF items — analysis only.

5. If the runtime provides `$DHF_CONTEXT.test_coverage.manual_verification_candidates`,
   use those item IDs as the starting point for `test_plan.must_be_manual`
   instead of guessing. Keep `auto_covered`, `needs_new_tc`, and
   `must_be_manual` aligned with the machine-readable coverage hints when they
   are present. Prefer real DHF item IDs in `needs_new_tc` when a specific
   requirement or risk needs new automated coverage. Use prose only when no
   DHF item ID applies; deterministic `@links:` enforcement only applies to
   ID entries.

6. Produce the spec at `docs/cr-specs/{{cr_id}}-Spec.md`.
   Keep it short. Do not enumerate hundreds of speculative risks or test cases.

7. Do not modify any file other than `docs/cr-specs/{{cr_id}}-Spec.md`.

## Triage: Classify the CR before writing the spec

Before populating the spec, determine the disposition by checking in order:

1. **duplicate** — search the DHF (`dhf item list`) and codebase. If the
   requested capability already exists, set `disposition: decline:duplicate` and
   reference the existing item ID or file path in `decline_rationale`.

2. **out-of-scope** — does the CR conflict with or fall outside the product
   direction? Set `disposition: decline:out-of-scope`. Explain what would need
   to change for it to be in scope.

3. **architecture-conflict** — does the CR require a design that violates a
   documented ADR or architectural constraint? Set `disposition:
   decline:architecture-conflict` and reference the constraint.

4. **too-large** — does the CR span multiple independent subsystems or require
   changes across more than ~3 DHF item types? Set `disposition:
   decline:too-large` and suggest 2-3 smaller CRs in `decline_rationale`.

5. **scope-expansion** — is the CR valid but beyond the current roadmap scope?
   Set `disposition: hold:scope-expansion`. Explain what stakeholder approval
   is needed.

6. **approve** — the CR is in scope and appropriately sized. Determine
   `pipeline_route`:
   - `doc-only`: only documentation or comment changes, no code or DHF items
   - `dhf-only`: DHF item updates only, no product code changes
   - `test-only`: test additions only, no new requirements or DHF items
   - `standard`: product code changes are required (with or without DHF item
     updates). If no DHF items need to change, keep `affected_items` and
     `proposed_new_items` empty instead of inventing DHF impact.

For `decline:*` and `hold:*`, only populate `cr_id`, `disposition`, and
`decline_rationale`. Leave all other fields at their defaults.

## Spec Format

The spec MUST begin with this YAML front-matter (machine-read by CI):

```
---
cr_id: "{{cr_id}}"
disposition: approve           # see disposition guide above
pipeline_route: standard       # standard|dhf-only|doc-only|test-only — only when disposition: approve
decline_rationale: ""          # required when disposition is not approve; omit when approve
affected_items: []             # existing DHF item IDs this CR touches — only when approved
proposed_new_items: []         # DHF items to create — only when approved
design_impact_summary: "..."   # 1-2 sentences — only when approved
test_plan:                     # only when approved
  auto_covered: []
  needs_new_tc: []
  must_be_manual: []
---
```

Markdown sections after the front-matter:
1. Summary
2. Implementation Plan
3. DHF Impact
4. Verification
5. Implementation Checklist
6. Open Questions
