# CR Implementation Task

You are implementing a Change Request for this product.

CR ID: {{cr_id}}

## Inputs

- CR item: `medharness --dhf DHF item get {{cr_id}}` — read this first; the
  `implementation_notes` field contains the reviewed implementation plan from
  the design phase; `affected_items` lists the DHF items (SRS, SWDD, etc.)
  produced by that phase
- DHF items linked in `affected_items` — read SWDD items for module-level
  design decisions; read SRS items for requirement detail and verification
  criteria
- Repository context: `AGENTS.md` (or `CLAUDE.md`), `README.md`

## Steps

Do not commit, push or open a pull request, whatever the repository's own
instructions say. Leave your changes in the working tree for whoever started
this run to commit.


1. Read the CR item. Follow the `implementation_notes` plan exactly — it was
   reviewed and approved as part of the design PR. Do not re-derive the
   approach or deviate from it unless you discover a concrete blocker, in
   which case note the deviation clearly in a comment.

2. Implement all changes required by the design. Check `AGENTS.md`/`CLAUDE.md` for the
   project's source layout, workspace names, and test file conventions.

3. Follow all coding conventions documented in `AGENTS.md`/`CLAUDE.md`.

4. Run build, tests, then coverage check.

   Check `AGENTS.md`/`CLAUDE.md` for the project's build, typecheck, and test commands,
   and for the JUnit output directory. Run in order — coverage requires the
   JUnit results produced by the test run:

   ```bash
   <typecheck command>
   <test command>                        # produces JUnit XML
   medharness --dhf DHF verify completion --cr {{cr_id}} --junit <junit-output-dir>
   ```

   `verify completion` checks exactly this CR's items: each requirement it
   touched must be verified by a passing test. If it reports an item without a
   passing test, write that test or put `@links:<ITEM_ID>` in the name of the
   relevant test(s) and re-run tests + coverage until it passes:

   ```ts
   it('@links:SRS-012 @testing:T1 authenticates within 2 s at p95 under nominal load', async () => {
     ...
   });
   ```

   A requirement's `testing` field lists its test points as `T<n>: <what is checked>`.
   Claim each point in the name of the test that checks it, as above
   (`@testing:T2`; pytest can set the `medharness.links` and `medharness.testing`
   JUnit properties instead). A point with no passing test
   fails `verify tests`. Never renumber a point; a test whose point changed
   follows the new wording.

   Use the `verification_criteria` field on each requirement item as the
   pass/fail condition for the test. If a requirement genuinely cannot be
   automated, set its `verification_method` to Inspection, Analysis or
   Demonstration (`medharness --dhf DHF item update <ID> --data
   '{"verification_method": ["Inspection"]}'`) and say why in
   `implementation_notes`. A comment in a test file is evidence of nothing:
   only a passing test that claims the ID, or a method that needs no test,
   satisfies `verify completion`.

5. **Reconcile implementation against the plan and DHF items.**

   Run `git diff $(git merge-base {{since_ref}} HEAD)` scoped to the source roots listed in `AGENTS.md`/`CLAUDE.md`
   to see every file changed.
   Then check:

   a. **Code vs implementation plan** — if the implementation deviated from
      `implementation_notes` (different file, different approach, extra edge
      case), update the field to reflect what was actually built:

          medharness --dhf DHF item update {{cr_id}} \
            --data '{"implementation_notes": "<updated plan>"}'

   b. **Code vs SWDD** — if a module ended up structured differently than its
      SWDD describes (component split, interface changed shape), update the
      SWDD to match:

          medharness --dhf DHF item update <SWDD-ID> \
            --data '{"content": "<updated description>"}'

   If nothing deviated, no updates are needed — do not make cosmetic edits.

6. Do not modify CR lifecycle or status fields.

7. Keep changes focused on what the CR describes — no unrelated refactoring or
   speculative additions.
