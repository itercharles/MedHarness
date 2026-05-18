# CR DHF Generation Task (Triage + V-Model Cascade)

You are working in the DHF repository. Given a single CR, your task is to triage
the request and — if approved — generate the **complete DHF item cascade** in one
session, reasoning top-down through the V-model hierarchy and writing items via
the medharness CLI.

CR ID: {{cr_id}}

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml`
- Repository context: `CLAUDE.md`, `README.md`
- Source code: relevant modules under `apps/`, `packages/`, or equivalent
  source roots described in `CLAUDE.md` — identify and read these based on
  what the CR touches before writing SWDD items

Read the CR item and repository context first, then identify which source
modules are relevant and read them before writing any SWDD items.

## Step 1: Triage

Before generating any DHF items, evaluate whether the CR should proceed.

**Triage checklist (evaluate in order):**

1. **Duplicate** — Does an existing CR or DHF item already address this request?
2. **Out-of-scope** — Is this outside the product's stated direction?
3. **Architecture-conflict** — Does this contradict an existing ADR or SYSARCH item?
4. **Too-large** — Would this require changes across 3+ major subsystems? If so, it
   should be split into smaller CRs.

**If the CR should be rejected**, update the CR item with the rejection reason and stop:

    python -m medharness --dhf DHF dhf item update {{cr_id}} \
      --data '{"status": "rejected", "impact_assessment": "<reason for rejection>"}' \
      --author "github-actions[bot]" --cr "{{cr_id}}"

Do **not** generate any DHF items if rejecting. Output a brief explanation of the
rejection reason and stop.

**If the CR is approved**, proceed to Step 2.

## Step 2: V-Model Generation

### Generation Order

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
               └─► SWDD  (implements SRS; module MODULE -- link both fields)

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

## SWDD Items

**SWDD items capture design decisions — choices that are not obvious from the
requirement alone.** Each SWDD item belongs to a software module (MODULE) and
must carry both `implements` (SRS IDs) and `module` (MODULE ID). List existing
MODULE items first to find or create the right module:

    python -m medharness --dhf DHF dhf item list --type MODULE

**Apply this threshold before creating or updating a SWDD:**

> *Would a competent developer, given only the SRS, make a meaningfully wrong
> architectural or structural choice without this SWDD?*

If no, skip the SWDD. Examples that do **not** warrant a SWDD:
- Visual-only changes: button color, spacing, typography, icon swap, layout
  position
- Copy or label changes
- Configuration value changes
- Trivial bug fixes where the fix is self-evident from the SRS

Examples that **do** warrant a SWDD:
- New module or service with non-trivial business logic
- Change to data flow, state management pattern, or caching strategy
- New or changed API contract (endpoint shape, auth mechanism, error codes)
- Algorithm or calculation change
- Integration with an external system or library

When a SWDD is warranted, read the source files for the module first:

1. Identify which source module(s) the SRS requirement maps to — use `CLAUDE.md`
   and the directory structure to find the right folder.
2. Read the relevant files. For a new module that does not exist yet, describe
   the intended design; for an existing module, describe the actual structure
   plus the changes the CR requires.
3. SWDD content should cover: module responsibility, key data structures or
   types, the main algorithm or control flow, and interfaces to adjacent modules.
   One SWDD item per logical module or component boundary — do not create one
   per function.

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

## Step 3: Implementation Plan

After all DHF items pass validation, write an implementation plan into the CR's
`implementation_notes` field. This plan is the primary input for the `develop-cr`
session — write it so a developer can implement the CR without re-reading the
source code or re-deriving design decisions.

**Format:**

```
## Overview
One paragraph: what this CR changes and why.

## Current State
Describe the relevant existing code — modules involved, key types, current
behaviour. Reference specific files and functions by name.

## Changes Required
For each area of change:
- **File / module**: what changes and why
- Distinguish: new file | modify existing | delete

## Implementation Steps
Ordered list of concrete steps. Each step should be independently verifiable.

## Edge Cases & Constraints
Anything a developer might miss: error paths, concurrency, backwards compat,
validation rules, regulatory constraints from the DHF items.

## Tests
What to test and at what level (unit / integration / manual). Reference the
SRS/SYS item IDs that each test covers.
```

Write this to the CR item:

    python -m medharness --dhf DHF dhf item update {{cr_id}} \
      --data '{"implementation_notes": "<plan>"}' \
      --author "github-actions[bot]" --cr "{{cr_id}}"

## Inline Validation Hook

After writing all DHF items and recording risk impact, validate and self-correct:

    python -m medharness --dhf DHF dhf validate schema
    python -m medharness --dhf DHF dhf validate traceability

If either reports errors introduced by your changes, fix them via `dhf item update`
and re-validate. Repeat until both pass cleanly.

## Step 2.5: Risk Impact Recording

After validation passes, explicitly record which existing RISK and RCM items are
relevant to this CR — even if they required no structural changes.

1. List all existing risk items:

       python -m medharness --dhf DHF dhf item list --type RISK
       python -m medharness --dhf DHF dhf item list --type RCM

2. For each, assess: does this CR change behavior that could alter the hazard
   likelihood, harm severity, or effectiveness of the control?

3. Collect the IDs of all affected items — those you created, updated, or
   determined are relevant but unchanged — and write them to the CR:

       python -m medharness --dhf DHF dhf item update {{cr_id}} \
         --data '{"affected_risk_items": ["RISK-001", "RCM-002"]}' \
         --author "github-actions[bot]" --cr "{{cr_id}}"

   Use `[]` if no risk items are relevant. Do not omit this step.

## Step 4: Write Design Record

After all items are created, validated, and risk impact recorded, add
`proposed_new_items` to the CR spec file. The `ci cr-complete` closure gate
reads this field to verify every promised item was actually materialised.

**Update the existing spec file — do not recreate it.** `DHF/documents/specs/{{cr_id}}-Spec.md`
is the approved analysis spec written by `cr-analyze`. Overwriting it destroys
required fields (`cr_id`, `pipeline_route`, `design_impact_summary`, `test_plan`).
Patch only the `proposed_new_items` key.

1. Collect every DHF item you **created** in this session — type code and title.
   Do not include items you only updated. Include all types: CRS, SYS, SRS,
   SYSARCH, SWDD, RISK, RCM, etc.

2. Patch the spec file:

```python
import yaml, pathlib, re

spec_path = pathlib.Path("DHF/documents/specs/{{cr_id}}-Spec.md")

proposed = [
    {"type": "SRS",  "title": "Rate limit input validation"},
    {"type": "RISK", "title": "Unintended data modification from concurrent edits"},
    {"type": "RCM",  "title": "Optimistic-lock concurrency control for edit sessions"},
    # one entry per item you created
]

if spec_path.exists():
    text = spec_path.read_text()
    parts = text.split("---", 2)          # ["", frontmatter_str, body]
    fm = yaml.safe_load(parts[1]) or {}
    fm["proposed_new_items"] = proposed
    spec_path.write_text("---\n" + yaml.dump(fm, default_flow_style=False) + "---" + parts[2])
else:
    # Spec not yet written — create a minimal one (unusual in normal workflow).
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "---\n" + yaml.dump({"disposition": "approve", "proposed_new_items": proposed},
                            default_flow_style=False) + "---\n\n# {{cr_id}} Design Record\n"
    )
```

   Each entry's `title` must match the `title:` field of the created DHF item.
   Matching at closure is case-insensitive and whitespace-trimmed.

   **Do not list items you updated but did not create.**
   **Do not confuse with `affected_risk_items`** (Step 2.5) — that records which
   RISK/RCM items are *relevant*; `proposed_new_items` records what was *created*.

## Scope Constraints

- Only create or update items **directly required** by this CR.
- Do not create items for hypothetical future changes.
- Do not modify files outside `DHF/`.
- Do not edit the CR item except to set `status: rejected` and `impact_assessment`
  when rejecting (Step 1), write `affected_risk_items` (Step 2.5), or write
  `implementation_notes` (Step 3).

## DHF Impact Skills
