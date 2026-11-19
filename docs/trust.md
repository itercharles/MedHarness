# How far to trust the checks

> **Stability:** Draft
> **Last reviewed:** 2026-11-19

An agent can write a change request, its impact analysis and its code. This page says what MedHarness checks of that, what it cannot, and what the reviewer still has to read. The tool's own risk ratings are in [validation.md](validation.md).

## What the checks guarantee

The checks are ordinary code, not a model: the same DHF and the same branch give the same result, every time. An AI stage proposes; a check compares what it proposed with the repository. Code checks what code can check, and puts the rest in front of the reviewer.

- `verify impact` compares what the branch changed with what the CR says. The items changed must be exactly the CR's `affected_items`. Every item that depends on a changed item, and every item whose module owns a changed file, must be changed or listed in `reviewed_items`. A changed file no module owns fails. Risk items linked to a change must be in `affected_risk_items`. The `impact_analysis` must be complete and name only items that exist.
- `verify tests` compares each requirement with the JUnit results. A requirement needs a passing test linked to it, a test must link to something real, and a test must claim only test points its requirement declares. With `--cr`, it asks this only of the items that CR changed.

Both read links and `paths` that the project wrote. A link nobody created cannot be seen by any check, so what a check can catch depends on the project's own traceability links and on its MODULE `paths` ([what `verify impact` reads](configuration.md#what-verify-impact-reads)).

## What it stopped, and what it did not

One honest change request passes every gate. Each row leaves one thing out of it, the way an agent might. The table is generated from the seeded-omission test (`tests/integration/test_seeded_omissions_are_stopped.py`); the same set runs on your machine with [`build validation`](adopting.md#validating-your-installation).

<!-- BEGIN GENERATED: seeded-count — python scripts/generate_interface.py -->
The seeded-omission set stops 9 of 12 ways of leaving something out of a change.
<!-- END GENERATED: seeded-count -->

<!-- BEGIN GENERATED: seeded-table — python scripts/generate_interface.py -->
| Left out of an honest change | Result |
|---|---|
| SRS-001 derives from the changed SYS-001; nobody looked at it. | Stopped by `verify impact` |
| SRS-001 changes instead of SYS-001; its parent SYS-001 is neither changed nor reviewed. | Stopped by `verify impact` |
| RCM-001 controls the changed SYS-001; the CR records no risk impact. | Stopped by `verify impact` |
| The dose calculation changes; the CR touches no item and claims no impact. | Stopped by `verify impact` |
| Beside the honest change, the export module changes too, and nothing in the DHF says why. | Stopped by `verify impact` |
| The CR marks itself rejected, so the export change it never accounted for goes unchecked. | Stopped by `verify impact` |
| The branch also rewrites UC-001, and the CR does not say so. | Stopped by `verify impact` |
| The CR says SWDD-001 changes; the branch leaves it alone. | Stopped by `verify impact` |
| The test that verified SYS-001 is gone from the results. | Stopped by `verify tests` |
| SYS-001 now requires something new; its test points are what they were. | **Not stopped:** test_points_unchanged warns, it does not stop |
| The code now rounds the dose; a new way to under-dose, and the risk dimension says not_required. | **Not stopped:** a hazard linked to nothing has no way in |
| The test still runs and passes, and no longer checks the dose. | **Not stopped:** a passing test is taken at its word |
<!-- END GENERATED: seeded-table -->

The three misses are known gaps, not oversights in this page:

- **Test points left unchanged.** The check warns that a changed requirement still carries its old test points. It does not stop the merge, because a point can stay true after a change.
- **A new hazard linked to nothing.** The risk check follows links from items the change reaches. A hazard the change creates, with no item pointing at it, has no way in.
- **A verifying test weakened.** A test that runs and passes is taken at its word. Whether it still checks the requirement is for a person.

## What the reviewer reads in every change request

1. **Each "reviewed, no change needed".** The check sees that an item was listed, not that it was read. Open the reasons for the ones that matter.
2. **Links the change should have.** A relationship nobody wrote is invisible. Ask whether the new or changed requirement is linked to its parent, design, and risk items.
3. **The tests, not only their results.** For each changed requirement, read the test that carries its link and ask whether it still checks the requirement.
4. **New hazards.** Read the code for ways to fail that the risk items do not name.
5. **Test points on changed requirements.** Read the warning, and update the points or say why they stand.
