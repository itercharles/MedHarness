# Tool validation

> **Stability:** Draft
> **Last reviewed:** 2026-10-26

What MedHarness is trusted to do, how much a wrong answer matters for each command, and the requirements and tests that back the commands rated high and medium. It is the start of [iteration 4](charter.md#iterations) of the charter.

ISO 13485 §4.1.6 asks a manufacturer to validate software used in its quality system in proportion to the risk, and IEC/TR 80002-2 describes how: state what the tool must do, rate the risk of it doing that wrongly, and keep evidence that it does it. This page does the first two for MedHarness; the repository's own DHF holds the requirements and the tests are the evidence.

## Intended use

MedHarness checks the design-control evidence of a software change and produces the release's evidence from it. A `verify` command judges what is in the repository and on the machine and answers pass or fail; `build release` and `build approvals` write what a release is shown by; `item` records the DHF. It does not decide whether a requirement, a risk conclusion or a change is right, it is not an eQMS, and it does not replace the review of a pull request or the signatures of a release. The [charter](charter.md) states the promises and the non-goals.

`build plan` and `build code` run an AI agent. They propose; the deterministic commands check what they propose, a person reviews it, and nothing relies on them being right. Their boundary is in [ai-security.md](ai-security.md).

## Risk of each command

The risk is what a wrong **pass** would cause: a command that fails something sound costs time and is noticed at once; one that passes something unsound can reach a release unseen.

| Risk | Commands | A wrong pass means |
|---|---|---|
| High | `verify completion`, `verify tests`, `verify approval --release`, `build release`, `verify impact`, `verify changes`, `verify dhf` | unverified, unapproved or untraced content is released, or an omission is hidden |
| Medium | `verify soup`, `item transition`, `item create` / `update`, `verify approval` without `--release`, `build approvals`, `build soup` | wrong data or a missed vulnerability, which a later gate checks again |
| Low | `item get` / `list`, `init` | nothing evidence depends on |
| Out of scope | `build plan`, `build code` | AI proposals, not relied on |

## MedHarness's own DHF

MedHarness keeps its requirements the way it asks its users to: as items in a DHF, here [`DHF/`](../DHF) at the root of this repository, checked by MedHarness itself. A tool's requirements are software requirements, so the DHF holds one item type, the SRS, and nothing else: `omit_doc_types` in [`DHF/config/global.yaml`](../DHF/config/global.yaml) leaves out the others, and with no other type there is no chain for coverage and no link to require (`traceability_matrices: []`, `required_traceability: []`; see [configuration](configuration.md#changing-the-defaults)).

Its SRS type is the shipped one with a `risk` property in place of `derives_from` ([`DHF/config/doc_types/srs.yaml`](../DHF/config/doc_types/srs.yaml)). `risk` is what a wrong pass of that behaviour would cause, rated `high`, `medium` or `low` by the table above. Each item states one behaviour of a gate, what it must pass and what it must stop, with `verification_method: [Test]`, measurable `verification_criteria` and numbered test points `T1`, `T2`, … in `testing`, one for each distinct case.

The tests that verify an item carry its ID and the point they cover:

```python
@pytest.mark.dhf_links("SRS-016")
@pytest.mark.dhf_testing("T2")
def test_a_signature_by_a_role_that_does_not_own_the_document_does_not_count(project): ...
```

The `dhfkit` pytest plugin writes both markers into the JUnit XML, and `verify tests` reads them. To check the whole thing locally:

```bash
pytest dhfkit/tests/ tests/ -q --junitxml=test-results/junit.xml
medharness --dhf DHF verify dhf --strict
medharness --dhf DHF verify tests --strict --junit test-results/junit.xml
```

CI runs exactly this in the job `Check | Own DHF`. The DHF is not part of the package: the wheel and the source distribution contain only `medharness` and `dhfkit`. To change a requirement, use `medharness --dhf DHF item create|update`, never the files; a change to behaviour changes its item and its test points in the same pull request.

## What is covered

| Command | Items | State |
|---|---|---|
| `verify completion` | SRS-002 to SRS-006 | covered |
| `verify impact` | SRS-007 to SRS-015 | covered |
| `verify approval --release` (and the approval log and approvers list it relies on) | SRS-016 to SRS-023 | covered |
| `verify tests` | SRS-024 to SRS-029 | covered |
| `verify changes` | SRS-030 to SRS-034 | covered |
| `verify dhf` | SRS-035 to SRS-042 | covered |
| `build release` | SRS-043 to SRS-050 | covered |
| `verify soup` | SRS-051 to SRS-054 | covered |
| `item create` / `update` | SRS-055 to SRS-059 | covered |
| `item transition` | SRS-060 to SRS-062 | covered |
| `verify approval` without `--release` | SRS-063 to SRS-065, with SRS-019, SRS-020 and SRS-022 for the log and the approvers list | covered |
| `build approvals` | SRS-066 and SRS-067 | covered |
| `build soup` | SRS-068 to SRS-070 | covered |
| Low risk commands | none | rated, not specified: nothing evidence depends on them |

"Covered" means every test point of every item has at least one passing test, which `verify tests --strict` enforces. It does not mean the requirements are complete for the command: an omission a requirement does not name is not tested. All seven high-risk commands and all six medium-risk ones are covered. The low-risk commands are rated and not specified, and the next step is a command that runs these tests where MedHarness is installed.

The requirements were derived from what the commands do today ([interface](interface.md), the gates' docstrings and the tests that already existed), and the tests were annotated, not rewritten. Where a case was untested, a test was added.
