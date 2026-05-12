# CR Analysis Prompt

You are working in the DHF repository for {{project_name}}.

## Inputs

- CR item: `DHF/items/{{cr_id}}.yaml`
- DHF context (pre-computed): environment variable `$DHF_CONTEXT` (JSON)
- Shared context: `AI-harness/context.md`
- Product repo: `{{product_repo}}`

## Phase 1 — Read context

Read the CR item YAML. Parse `$DHF_CONTEXT` for:
- Current SRS/CRS items and their lifecycle states
- Open traceability gaps
- Recent CR history

## Phase 2 — Analyze

Determine:
1. **Direction fit**: Does this CR align with existing SRS scope, or does it expand it?
2. **Affected DHF items**: Which existing items (by ID) need to be updated?
3. **New items needed**: Are new SYS/SRS/SWDD items required?
4. **Test plan**: Read `$DHF_CONTEXT.test_coverage.coverage_by_item` for `auto_covered`
   (item IDs already have linked passing TCs). Read
   `$DHF_CONTEXT.test_coverage.uncovered_requirements` for `needs_new_tc`
   (items with no TC coverage). Read
   `$DHF_CONTEXT.test_coverage.manual_verification_candidates` for structured
   `must_be_manual` candidates and cite the reported reasons. Do not guess —
   use the computed coverage data.

## Phase 3 — Write spec

Write the spec to `DHF/documents/specs/{{cr_id}}-Spec.md`.

The spec MUST begin with this YAML front-matter block (machine-readable):

```yaml
---
cr_id: "{{cr_id}}"
direction_fit: "in-scope"        # in-scope | scope-expansion | out-of-scope
affected_items:
  - SYS-012
  - SRS-034
proposed_new_items:
  - type: SRS
    title: "Brief title of new item"
design_impact_summary: "..."   # 1-2 sentences summarizing overall design impact
test_plan:
  auto_covered:
    - TC-SYS-012-001
  needs_new_tc:
    - linked_to: SRS-034
      description: "Test that..."
  must_be_manual:
    - description: "Why automation is not feasible"
---
```

After the front-matter, write:
- Problem Summary — what and why
- Technical Approach — how (DHF + product code)
- DHF Items — full list with proposed changes
- Product Code Changes — files, functions, APIs to touch
- Verification — how to confirm correctness
- Compliance Notes — traceability, IEC 62304 class implications

## Phase 4 — Validate

Run `medharness dhf validate schema` and confirm no errors introduced.
Do NOT modify any DHF items directly — spec only.
