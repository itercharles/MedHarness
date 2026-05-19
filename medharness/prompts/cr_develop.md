# CR Implementation Task

You are implementing a Change Request for this product.

CR ID: {{cr_id}}

## Inputs

- CR item: `DHF/items/09_cr/{{cr_id}}.yaml` — read this first; the
  `implementation_notes` field contains the reviewed implementation plan from
  the design phase; `affected_items` lists the DHF items (SRS, SWDD, etc.)
  produced by that phase
- DHF items linked in `affected_items` — read SWDD items for module-level
  design decisions; read SRS items for requirement detail and verification
  criteria
- Repository context: `CLAUDE.md`, `README.md`

## Steps

1. Read the CR item. Follow the `implementation_notes` plan exactly — it was
   reviewed and approved as part of the design PR. Do not re-derive the
   approach or deviate from it unless you discover a concrete blocker, in
   which case note the deviation clearly in a comment.

2. Implement all changes required by the design. Check `CLAUDE.md` for the
   project's source layout, workspace names, and test file conventions.

3. Follow all coding conventions documented in `CLAUDE.md`.

4. Run build, tests, then coverage check.

   Check `CLAUDE.md` for the project's build, typecheck, and test commands,
   and for the JUnit output directory. Run in order — coverage requires the
   JUnit results produced by the test run:

   ```bash
   <typecheck command from CLAUDE.md>
   <test command from CLAUDE.md>        # produces JUnit XML
   medharness ci test-coverage --dhf DHF --junit-dir <junit-output-dir>
   ```

   If `test-coverage` reports uncovered requirements, add `@links:<ITEM_ID>`
   annotations to the relevant test(s) and re-run tests + coverage until it
   passes:

   ```ts
   // @links:SRS-012
   it('authenticates within 2 s at p95 under nominal load', async () => {
     ...
   });
   ```

   Use the `verification_criteria` field on each requirement item as the
   pass/fail condition for the test. If a requirement genuinely cannot be
   automated, add a `// @links:SRS-xxx manual` comment in the nearest test
   file and note it in `implementation_notes`.

6. **Reconcile implementation against the plan and DHF items.**

   Run `git diff origin/main` scoped to the source roots listed in `CLAUDE.md`
   to see every file changed.
   Then check:

   a. **Code vs implementation plan** — if the implementation deviated from
      `implementation_notes` (different file, different approach, extra edge
      case), update the field to reflect what was actually built:

          python -m dhfkit --dhf DHF item update {{cr_id}} \
            --data '{"implementation_notes": "<updated plan>"}' \
            --author "github-actions[bot]" --cr "{{cr_id}}"

   b. **Code vs SWDD** — if a module ended up structured differently than its
      SWDD describes (component split, interface changed shape), update the
      SWDD to match:

          python -m dhfkit --dhf DHF item update <SWDD-ID> \
            --data '{"content": "<updated description>"}' \
            --author "github-actions[bot]" --cr "{{cr_id}}"

   If nothing deviated, no updates are needed — do not make cosmetic edits.

7. Do not modify CR lifecycle or status fields.

8. Keep changes focused on what the CR describes — no unrelated refactoring or
   speculative additions.
