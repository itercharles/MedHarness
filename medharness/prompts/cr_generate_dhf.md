# CR Impact Analysis and DHF Generation

You are working in the DHF repository. Given a single CR, triage it, work out
what it changes and what it leaves alone, and write the DHF items that follow,
using the medharness CLI.

CR ID: {{cr_id}}

## Inputs

- CR item: `medharness --dhf DHF item get {{cr_id}}`
- Repository context: `AGENTS.md` (or `CLAUDE.md`), `README.md`
- Source code: the modules the CR touches, as `AGENTS.md`/`CLAUDE.md` describe
  the source roots. Read them before writing any SWDD item.

The DHF context below lists the project's types, links and chains. For a large DHF
it lists only the entry-tier items; query the rest with the CLI (see CLI Commands).

## Step 1: Characterise

Before judging the CR, write down what it asks for:

- The **behaviour delta**: "X changes from A to B", where A is what the product does
  today and B what the CR asks. Read the code and tests to establish A; take B from
  every part of the CR — its description counts as much as its acceptance criteria,
  including specifics such as where, when and what exactly.
- Its category: changed behaviour, defect, new capability, non-functional, dependency,
  or removal.
- Where the CR is ambiguous, the reading you will work with, as a string in
  `impact_analysis.assumptions`.

## Step 2: Triage

**Checklist (evaluate in order):**

1. **Duplicate** — Only when A already equals B in every detail of Step 1's delta.
   If any part of B is not yet true, or you are unsure, it is not a duplicate: approve
   it as a change to existing behaviour and anchor on what already exists.
2. **Out-of-scope** — Is this outside the product's stated direction?
3. **Architecture-conflict** — Does this contradict an existing ADR or SYSARCH item?

**To reject** (duplicate, out-of-scope or architecture-conflict), record the reason
and stop. Generate no items; reply with a brief explanation:

    medharness --dhf DHF item update {{cr_id}} \
      --data '{"status": "rejected", "impact_assessment": "<reason for rejection>"}'

**Otherwise approve** and record the triage:

    medharness --dhf DHF item update {{cr_id}} \
      --data '{"triage_result": {"verdict": "approved", "complexity": "<small|medium|large>", "affected_subsystems": ["<name>"], "related_crs": [], "notes": "<one sentence: why approved and the key constraint>"}}'

Complexity: `small` = 1 subsystem, <5 items likely; `medium` = 2 subsystems or
5–15 items; `large` = 3+ top-level branches or >15 items. A change that spans several
top-level branches is still approved with `complexity: large`; say in `notes` how it
should be split into smaller CRs.

## Step 3: Locate

Find where the change lands, in this order:

1. **Test files first.** Every requirement has a test. Search them for the CR's
   words, UI strings, routes and component names (`git grep -n -i "<term>" -- <test dirs>`).
   Follow each match's `@links:` tag or `medharness.links` property to requirement IDs.
2. **Drill down.** Read the entry-tier items one line each
   (`medharness --dhf DHF item list --type <ENTRY_TYPE> --brief`), pick the 2–3
   suspect branches, and follow them down with
   `medharness --dhf DHF item list --linked-to <ID> --brief`.
3. **Fall back to text search**: `medharness --dhf DHF item list --match "<words>" --brief`,
   rewording the CR in the DHF's own vocabulary.

Record each place the change lands as an anchor with its evidence. When nothing
credible matches, say so in `assumptions` and treat the change as a new capability
attached top-down.

## Step 4: Propagate and decide

Work from a queue that starts with the anchors. For each item, decide:

- **unchanged** — still true after the change; record why.
- **update** — edit it in place.
- **create** — only when no existing item can be updated; record why none could.

Preference: unchanged > update > create. A tier is touched only when the change
alters it; a user-facing feature does not need a full chain from the top to the
bottom.

**Does it belong in the DHF?** A user-visible capability that no requirement covers
belongs in the DHF when it affects clinical use, patient data or safety; when it is
part of the intended use, labelling or instructions for use; or when the project
wants it verified and regression-tested like a requirement. Use the DHF scope in
`AGENTS.md`/`CLAUDE.md` where the project states one. Past CRs that changed no item
are not a scope rule. If you keep a user-visible capability out of the DHF, name the
criterion it fails in the `requirements` dimension and in `assumptions`, so the
reviewer can overrule it.

When you change an item, put its neighbours on the queue: its parents and children,
the risk controls that implement it and the risks they mitigate, architecture and
design items, siblings under the same parent (check for conflict and overlap), and
its test points. Stop at items you decide are unchanged. Create in chain order, so
links can name items that already exist.

Read an existing item before deciding. Do not write an item for a hypothetical
future change.

## Step 5: Gaps

Go through each dimension below and record a verdict: `required`, `not_required` or
`follow_up`, with a reason and the items it touches. Create what is missing (a new
hazard, a new SOUP item, a new test point) and queue its neighbours too.

- **product** — Does the change alter a user workflow or a user need? `not_required`
  when the existing use cases and needs stay accurate (a fix, a label, a layout).
- **requirements** — Are the requirements the change touches still correct,
  measurable and free of conflict with their siblings? `not_required` only when no
  requirement's meaning moves.
- **architecture** — Does it change boundaries, data flow, shared contracts or
  deployment? `not_required` for local behaviour inside one module.
- **risk** — Does it add a hazard, weaken or bypass a risk control, or alter data
  integrity or a safety-relevant user action? `not_required` when no hazard, control
  or data path is affected. List every RISK and control you assessed, changed or not.
- **soup** — Does it add, remove, upgrade or re-purpose third-party software?
  `not_required` when existing dependencies are used as before.
- **test** — Which requirements need a new or changed test point, and at what level
  (unit, integration, manual)? `not_required` only when no expectation changes.
- **regulatory** — Does it change intended use, indications, patient or user
  population, labelling or instructions for use, or device identification (UDI)?
  `not_required` when none of these moves.
- **security** — Does it change authentication, authorisation, a network or API
  surface, handling of personal or protected data, input parsing, encryption or
  secrets? `not_required` when none of these changes.
- **usability** — Does it change what users see, the steps they take, error handling
  or alerts, or the visibility of safety-relevant information? `not_required` when
  the interaction is the same.

Use `follow_up` for a consequence that belongs in another change, and say which.

## Step 6: Write and validate

Write items with the CLI (see CLI Commands), then validate:

    medharness --dhf DHF verify dhf

Fix what it reports with `medharness item update` and run it again until it is clean.

Then record the result on the CR in one update:

- `affected_items` — every item you created or updated, not the CR itself.
  `medharness verify changes --cr {{cr_id}}` compares this list with what the branch
  changes, in both directions.
- `reviewed_items` — every item you examined and left unchanged that depends on a
  changed item or that a check may require. Each must have an `unchanged` entry.
- `affected_risk_items` — every RISK and RCM item that is relevant, changed or not;
  `[]` when none. Do not omit it.
- `impact_analysis` — the record of Steps 1–5 (shape below).
- `implementation_notes` — the plan (format below).

      medharness --dhf DHF item update {{cr_id}} --data '{"affected_items": [...], "reviewed_items": [...], "affected_risk_items": [...], "impact_analysis": {...}, "implementation_notes": "..."}'

### impact_analysis

```yaml
impact_analysis:
  assumptions:            # how ambiguities in the CR were resolved
    - "<string>"
  anchors:                # where the change lands, and why you believe it
    - id: <ID>            # must also be in affected_items or reviewed_items
      evidence: "<test file and tag, item text, or search that found it>"
  unchanged:              # every item examined and left alone — one per reviewed_items entry
    - id: <ID>
      reason: "<why it still holds>"
  created:                # one per item this CR created
    - id: <ID>
      reason: "<why no existing item could be updated instead>"
  dimensions:             # all nine, each once
    - dimension: <product|requirements|architecture|risk|soup|test|regulatory|security|usability>
      verdict: <required|not_required|follow_up>
      reason: "<why>"
      items: []           # IDs this dimension touches
```

The check after your work also requires: each parent of a created or updated
requirement is in `affected_items` or `reviewed_items`; each
risk control that implements a changed item, and each risk it mitigates, is in
`affected_risk_items`.

### implementation_notes

The primary input for the `build code` session: write it so a developer can implement
the CR without re-reading the source or re-deriving design decisions.

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
requirement IDs and test points (`Tn`) that each test covers.
```

## verification_criteria Field (CRS, SYS, SRS only)

For every CRS, SYS, and SRS item you create or update, populate
`verification_criteria` with a concise, **measurable** criterion:

- State observable outcomes, thresholds, or pass/fail conditions.
- Avoid vague language ("works correctly", "behaves as expected").
- Example: "The system shall authenticate users within 2 seconds at the 95th
  percentile under nominal load conditions."

If an existing CRS/SYS/SRS you update has no `verification_criteria` or a vague one,
improve it. SWDD, RISK and RCM items do not carry it.

## Test points

Do not create TC items. A requirement's `testing` field lists its test points, one
per line, as `T<n>: <what is checked>`:

- A number never changes once used.
- A changed expectation edits `Tk` in place.
- A new case of the same behaviour adds `T<n+1>`.
- A test claims a point with `@testing:Tn` beside `@links:<ID>` in its name (or the
  `medharness.testing` JUnit property).

## SWDD Items

**An SWDD captures a design decision that is not obvious from the requirement alone.**
Each carries `implements` (SRS IDs) and `module` (a MODULE ID); list existing MODULE
items first (`medharness --dhf DHF item list --type MODULE`).

Apply this threshold before creating or updating one:

> *Would a competent developer, given only the SRS, make a meaningfully wrong
> architectural or structural choice without this SWDD?*

If no, skip it. Not warranted: visual-only changes (colour, spacing, layout, icon),
copy or label changes, configuration values, trivial fixes obvious from the SRS.
Warranted: a new module or service with non-trivial logic; a change to data flow,
state management or caching; a new or changed API contract; an algorithm or
calculation change; an integration with an external system or library.

When one is warranted, read the module's source first. For a new module describe
the intended design; for an existing one, the actual structure plus the change.
Cover the module's responsibility, key types, the main control flow and the
interfaces to adjacent modules. One SWDD per module or component boundary, not per
function.

**When the project's chains require a SWDD for a new SRS** (the check reports an SRS
with no covering SWDD) and the threshold above is not met, cover it with the existing
SWDD of the module whose code the change touches: add the SRS to its `implements` and
one line to its content. Create a SWDD only when no existing one covers that code, and
a MODULE only when the code lives in no existing module.

## CLI Commands

    medharness --dhf DHF item create --type <TYPE> --data '<JSON>'    # ID assigned automatically
    medharness --dhf DHF item update <ITEM_ID> --data '<JSON>'
    medharness --dhf DHF item get <ITEM_ID>
    medharness --dhf DHF item list --type <TYPE>
    medharness --dhf DHF item list --brief                    # id, type, title, links only
    medharness --dhf DHF item list --match "<words>"         # every word, any field, case-insensitive
    medharness --dhf DHF item list --linked-to <ITEM_ID>    # items linked to or from it

The options combine. Do **not** write YAML files directly.

## Scope Constraints

- Only create or update items **directly required** by this CR.
- Do not modify files outside `DHF/`, and do not modify `DHF/config/`. If the CLI
  rejects a field, stop and report it; do not change the schema to fit.
- Do not commit, push or open a pull request, whatever the repository's own
  instructions say. Leave your changes in the working tree for whoever started
  this run to commit.
- Do not move the CR through its lifecycle.
- Do not edit the CR item except: `status: rejected` and `impact_assessment` when
  rejecting (Step 2); `triage_result` (Step 2); `affected_items`, `reviewed_items`,
  `affected_risk_items`, `impact_analysis` and `implementation_notes` (Step 6).
