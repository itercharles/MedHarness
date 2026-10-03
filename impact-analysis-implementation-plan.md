# Implementation plan: the change-impact analysis process in `build plan`

Source design: "DHF 变更影响分析流程" (Claude doc). This plan implements the parts
that can be decided now. The gold set and the deterministic test-search index are
**out of scope** (they wait on the owner's decision about ContourLab history).

Branch: `feat/impact-analysis-process` from `origin/main`. One commit per work
package (WP), in order. Do not push, do not open a PR.

Follow `CLAUDE.md` throughout — in particular: test at the interface, unit-test only
logic worth isolating, no speculative fields, no comments that retell history,
`dhfkit` must not import `medharness`, every command answers JSON on stdout, and
docs ship with code (`python scripts/generate_interface.py` after any CLI change).

Run `.venv/bin/pytest dhfkit/tests/ tests/ -q` after every WP; it must pass.

## Decisions already taken (do not reopen)

| Question | Decision |
|---|---|
| Where "looked at but not changed", reasons and dimension verdicts live | A **new CR field `impact_analysis`** (structured, no `format`, like `triage_result`). `impact_assessment` keeps its rejection-reason role. `reviewed_items` stays the ID list `verify changes` reads |
| Where the new checks run | Inside `build plan` (`validate_generate_dhf`), so the existing fix pass corrects them. **Not** in any `verify` command |
| Who drives the work queue | The agent, guided by the prompt. Code checks closure afterwards |
| Locating from an issue that names no IDs | Prompt-driven: the agent searches **test files** first (every requirement has a test), then drills down top-down; evidence is recorded in `impact_analysis.anchors` |
| Granularity definitions (SYS vs SRS) | Not in this round |

## The `impact_analysis` shape

Written by the agent on the CR during `build plan`:

```yaml
impact_analysis:
  assumptions:            # list of strings; how ambiguities in the issue were resolved
    - "'release date' means the build date shown in the About box"
  anchors:                # where the change lands, and why we believe it
    - id: SRS-207
      evidence: "apps/client/e2e/about.spec.ts 'shows version' @links:SRS-207"
  unchanged:              # every item examined and left unchanged, with the reason
    - id: SYS-012
      reason: "Still satisfied: SYS-012 already requires product identification"
  created:                # every item this CR created, and why no existing item was updated instead
    - id: SRS-311
      reason: "No existing SRS covers export naming; SRS-204 is import-only"
  dimensions:             # all nine, each with a verdict
    - dimension: risk     # one of: product, requirements, architecture, risk, soup, test, regulatory, security, usability
      verdict: not_required   # required | not_required | follow_up
      reason: "Display-only change; no hazard, control or data path affected"
      items: []           # IDs this dimension touches (may be empty)
```

---

## WP1 — Prompt rewrite (`medharness/prompts`, `prompt_assembly.py`, `context.py`)

Goal: the plan prompt follows the 0–6 process, stops pushing toward over-creation,
and loses product-specific and stale text. Target: the assembled plan prompt for the
template project is clearly shorter than today (measure before/after with
`len(prompt)`; report both numbers in the commit message).

1. **Rewrite `cr_generate_dhf.md`** around the process, in this order:
   - Step 1 Triage (keep the checklist and the `triage_result` write). Replace
     "Too-large → reject" with: a change spanning several top-level branches is
     still triaged `approved` with `complexity: large`; say in `notes` how it should
     be split. Rejection stays for duplicate / out-of-scope / architecture-conflict.
   - Step 2 Characterise: write the behaviour delta ("X changes from A to B"), the
     category (changed behaviour, defect, new capability, non-functional, dependency,
     removal) and any ambiguity resolved, into `impact_analysis.assumptions`.
   - Step 3 Locate, in this order:
     1. Search the **test files** for the issue's words, UI strings, routes and
        component names (`git grep -n -i`); follow each match's `@links:` /
        `medharness.links` to requirement IDs. Every requirement has a test, so this
        is the primary route.
     2. Drill down: read the entry-tier items one line each
        (`item list --type <entry type> --brief`), pick the 2–3 suspect branches,
        follow them down with `item list --linked-to <ID> --brief`.
     3. Fall back to `item list --match "<words>" --brief`, rewording the issue in
        the DHF's vocabulary.
     Record each anchor with its evidence. When nothing credible matches, say so in
     `assumptions` and treat the change as a new capability attached top-down.
   - Step 4 Propagate and decide (the work queue): start from the anchors; for each
     item decide **unchanged (with reason) / update / create beside it**; for each
     item you change, put its neighbours on the queue — parent(s), children, risk
     controls that implement it and the risks they mitigate, architecture/design
     items, siblings under the same parent (conflict / overlap check), and its test
     points. Stop at items decided unchanged. Change preference: unchanged > update >
     create. A tier is touched only when the change alters it — there is no rule that
     a user-facing feature needs a full UC→SRS chain.
   - Step 5 Gaps: go through the nine dimensions (inline checklist, see item 3) and
     record a verdict for each; create anything missing (new hazard, new SOUP, new
     test point) and put it on the queue too.
   - Step 6 Write and validate: item create/update via CLI; `verify dhf` until clean;
     then write `affected_items`, `reviewed_items` (every item in `unchanged` that a
     check may require), `affected_risk_items`, `impact_analysis`,
     `implementation_notes`. Keep the existing `implementation_notes` format.
   - Keep: the `verification_criteria` rules, the SWDD threshold and its examples,
     the CLI section, scope constraints (update the list of CR fields the agent may
     write to include `impact_analysis`).
   - **Test points**: replace the "TC-SYS-001-001" paragraph with the T-point rules:
     `T<n>:` lines in a requirement's `testing` field; numbers never change; a changed
     expectation edits `Tk` in place; a new case of the same behaviour adds `T<n+1>`;
     tests claim them with `@testing:Tn` beside `@links:<ID>` (or `medharness.testing`).
   - Fix the step order (today Step 2.5 appears after Step 3) and "repeat until both
     pass" (there is one command).
2. **Delete the nine skill files and `_append_skills`** (`medharness/prompts/skills/`,
   `_SKILL_FILES`, `_load_skill`); remove the package if empty and fix packaging
   guards/`pyproject` if they list it.
3. **Inline the dimensions checklist** in `cr_generate_dhf.md` Step 5: one short block
   per dimension (product, requirements, architecture, risk, soup, test, regulatory,
   security, usability): what to check, when `not_required` applies. Generic and
   role-based only — **no** references to `DHF/documents/plans/*.md`, no DICOM /
   RTSTRUCT / contouring / dose wording, no "approved spec" two-stage language. Keep
   regulatory items that are product-neutral (intended use, labelling/IFU, UDI).
4. **`prompt_assembly.py` "Design layer roles"** (around line 116): remove "one per SYS
   requirement" / "one per SRS requirement". SYSARCH records a system-level design
   decision for the SYS it designs, only when the change alters boundaries, data flow
   or deployment; SWDD only past the threshold in the prompt.
5. **Plan context for a large DHF** (`_render_plan_context`): when `scope ==
   "whole_dhf"` and there are more than `MAX_ITEMS` items, do **not** list the first
   N alphabetically. Instead list only items of the chains' entry types (first type of
   each coverage chain) one line each, plus the type counts, plus one line telling the
   agent to use `item list --brief/--match/--linked-to`. At or under `MAX_ITEMS`, keep
   listing all. Set `MAX_ITEMS = 300`.
6. **Risk lines bug** (`context.py` `_risks`): it reads `severity` / `risk_level`,
   which the template RISK does not have, so every line renders `[— · —]`. Delete
   both keys and the bracket in the renderer.
7. **`cr_review_code.md`**: remove the `test_plan.needs_new_tc` references and the
   "spec" wording; replace `git diff origin/main -- apps/ packages/` with a diff of
   everything except the DHF and `docs/reviews/`.
8. `req_manage`'s "CR completed → transition" disappears with the skills; make sure no
   remaining prompt tells `build plan` to transition the CR.

Tests: prompt text itself is not testable — say so in the commit message. Test what
code renders: the plan prompt for a DHF above `MAX_ITEMS` lists entry-type items and not
the others; at/below it lists all; risk lines carry no `[— · —]`; the prompt contains no
"one per SRS requirement", no `development_plan.md`, no `DICOM`. Put these where the
existing prompt-assembly tests are (`tests/unit/test_cr_context.py` /
`test_a_running_agent_gets_the_same_instructions.py` — read them first).

## WP2 — `item list` retrieval options (`medharness/cli/item.py`)

Add three options; they combine with `--type` and with each other (AND):

| Option | Behaviour |
|---|---|
| `--match TEXT` | Keep items where **every** whitespace-separated term occurs, case-insensitively, in any string value of the item (including strings inside lists/dicts). Empty or whitespace-only → exit 1 with an error on stderr |
| `--linked-to ID` | Keep items that link to ID or that ID links to (use the item's `all_linked_uids` and ID's own). Unknown ID → exit 1, "Item 'X' not found." |
| `--brief` | One JSON object per line with only `id`, `type`, `title`, `links` (the item's `all_linked_uids`) |

The filtering is analysis, so it lives in `medharness`, not in `dhfkit`'s store
(`tests/guards/test_storage_does_not_analyse.py`). Keep stdout JSON-per-line and the
count on stderr. Regenerate `docs/interface.md`.

Tests (CliRunner, interface): each option alone; combined with `--type`; multi-term
match; CJK text match; `--brief` exact keys; bad input (empty `--match`, unknown
`--linked-to`); no matches → exit 0, nothing on stdout, `(0 item(s))` on stderr. Extend
`tests/unit/test_cli_item_list.py` if that is where `item list` is tested today.

## WP3 — `impact_analysis` field and closure checks (`design_validation.py`, `impact.py`, CR schema)

1. Add `impact_analysis` to `dhfkit/templates/config/doc_types/cr.yaml` (no `format`,
   label "Impact Analysis", a one-line comment naming the keys, as `triage_result` has).
   The repo's own `DHF/config/doc_types/cr.yaml` overrides CR: add it there too only
   if a test or guard needs it; otherwise leave the repo DHF alone and mention it.
2. New checks in `validate_generate_dhf`, skipped for a rejected CR (as
   `_check_cr_workflow_fields` does). Each error is `{field, issue, fix}` with a fix the
   agent can run, like the existing ones. Let A = `affected_items` ∪ created ∪ updated,
   R = `reviewed_items`, K = `affected_risk_items`.
   - `impact_analysis` present, a mapping, with all five keys; `dimensions` holds each
     of the nine names exactly once, `verdict` ∈ {required, not_required, follow_up},
     non-empty `reason`.
   - Every ID anywhere in `impact_analysis` exists in the DHF.
   - Every anchor ID ∈ A ∪ R, with non-empty `evidence`.
   - Every created item has a `created` entry with a non-empty reason.
   - Every ID in R has an `unchanged` entry with a non-empty reason.
   - Every ID in a dimension's `items` ∈ A ∪ R ∪ K.
   - **Upward**: each parent of a created or updated item (targets of its chain link
     fields — the same edges `impact.dependents` follows, reversed) ∈ A ∪ R. Add a
     pure helper in `impact.py` beside `dependents`; do not duplicate the edge
     building — factor it so both use one function.
   - **Risk**: for each created/updated item, every item of role `risk_control` that
     links to it, and every item of role `risk` such a control links to, ∈ K; a
     created/updated risk or risk-control item itself ∈ K. Resolve roles from config,
     not hard-coded `RISK`/`RCM` codes.
3. **Near-duplicate warning** (warning, not error — does not trigger the fix pass):
   for each created item, compare normalised `title + content` with every other item
   of the same type that was not created in this run, using `difflib.SequenceMatcher`
   ratio (works for CJK). At ≥ 0.75, warn naming the closest item and the ratio. Wire
   it next to `check_verification_quality` in `cr_generation.py` (~line 865).
4. The shape check is a judge with many branches: unit-test it directly. Then
   interface tests through `build plan` with the fake model
   (`tests/fixtures/fake_claude.py`, see `tests/integration/test_generate_dhf_e2e.py`
   and `test_change_impact.py`): a complete `impact_analysis` → no new errors; missing
   field → error naming it; a parent neither changed nor reviewed → error; an RCM
   implementing a changed SYS not in K → error; a created item without reason → error;
   a near-duplicate created item → a warning in the answer.
5. Docs: `docs/adopting.md` CR-field table (~line 253: add `impact_analysis`, renumber
   the "Written by" steps to the new prompt's steps); a `CHANGELOG.md` Unreleased entry,
   including that a project overriding the CR doc type must add `impact_analysis`
   (same wording style as the `reviewed_items` note). Regenerate `docs/interface.md` if
   report models change.

## WP4 — Design review sees what was not changed (`cr_review_design.md`, `cr_generation.py`)

1. Before the design review runs, render a **neighbourhood block** for each created or
   updated item and append it to the review prompt (deterministic, from the DHF):
   its parent chain up to the entry tier (`ID — title`), its siblings under the same
   parent(s), and for created items the closest same-type item from WP3's similarity
   (if ≥ 0.75). Cap siblings at 15 per item with a count of the rest.
2. Add to `cr_review_design.md`: read the CR's `impact_analysis`; judge (a) **Omission**
   — given the issue and the neighbourhood, is an item that should have been examined
   missing from `anchors`/`unchanged`/changed; (b) **Overlap** — should any created item
   have been an update of a neighbour; (c) **Conflict** — does a changed item contradict
   a sibling or parent; (d) whether each `unchanged` reason and dimension verdict holds.
   Keep the existing three questions and the output format.
3. Tests: the review prompt for a CR with a changed SRS contains its parent SYS and a
   sibling SRS; a created item with a near-duplicate names it. Prompt wording itself:
   state in the commit message that it is untestable.

## Done means

- Four commits on `feat/impact-analysis-process`, full suite green,
  `docs/interface.md` regenerated and its guard green.
- A final note listing: each WP item and where it was done (file:line), anything
  deviated from and why, anything left undone, and the before/after plan-prompt length.
