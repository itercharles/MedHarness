# Adopting MedHarness

## Starting fresh

Run `medharness init` in an empty directory. You get a complete DHF scaffold with sample items, config, document templates, and plans. Four things to replace before your first real CR:

1. Items in `DHF/items/` — delete the sample YAML files and add your own (or leave samples while you learn the schema)
2. Plan documents in `DHF/documents/plans/` — fill in your project-specific plans (SDP, SMP, etc.)
3. `DHF/config/global.yaml` — set your project name
4. `AI-harness/context.md` — describe your product so Claude reasons about the right domain

Commit the result and start writing CRs. Everything else — the CI workflow, document generation, traceability — works against whatever items you've put in.

## Bringing an existing DHF

MedHarness stores DHF content as YAML items, one file per record. Each item has a `type` that maps to a position in the V-model:

| Type | V-model layer |
|------|--------------|
| `UC` | Use cases |
| `CRS` | Customer requirements |
| `SYS` | System requirements |
| `SRS` | Software requirements |
| `RISK` | Hazard and risk analysis |
| `RCM` | Risk control measures |
| `SWDD` | Software detailed design |
| `SOUP` | Software of unknown provenance |
| `CR` | Change requests |
| `REL` | Release baselines |

Artifacts from common sources map directly to item types. A requirements spreadsheet becomes SRS and SYS items — one row per item, with `title` and `content` fields. A risk register becomes RISK items paired with RCM items (each RCM carries a `mitigates` field pointing to the RISK ID it controls). A SOUP list becomes SOUP items with `name`, `version`, and `purpose` fields.

What you do not need to migrate: test code (it stays in pytest, linked to DHF items via `medharness.links` annotations in JUnit output), generated documents (they are produced from items on demand), and CI scripts (use the scaffolded workflow from `init`). Migration is writing YAML files. The schema is self-documenting — look at the sample items from `init` to see every field and its expected values.

Traceability links between items are typed fields on child items (`derives_from`, `satisfies`, `implements`, `mitigates`, etc.). Run `medharness ci dhf-validate --dhf DHF` at any point to check link integrity. The validator tells you exactly which links are broken.

## Using dhfkit standalone

`dhfkit` is the DHF engine inside MedHarness — it ships as part of the same package (`pip install medharness`), not as a separate PyPI distribution. If your team has its own orchestration and only needs the engine layer — item storage, traceability graphs, lifecycle transitions, document generation — you can import from `dhfkit` directly and ignore the `medharness` CLI harness and AI workflow entirely. It has no dependency on the CI gates or prompt assembly layer. The `LocalDHFAdapter` gives programmatic access to items; the document generation pipeline is available separately. This is the right entry point for teams integrating DHF tooling into an existing CI system rather than adopting the full CR workflow.

## Test-driven development with test points

MedHarness supports TDD at the DHF level. The idea is that test intent is expressed in the design, not retrofitted after code is written.

Each requirement (CRS, SYS, SRS) has a `testing` field where you write numbered test points at design time:

```yaml
id: SRS-012
title: "Password must be at least 12 characters"
content: "The system shall reject passwords shorter than 12 characters."
testing: |
  T1: Given a password of 11 characters, registration returns a validation error.
  T2: Given a password of exactly 12 characters, registration succeeds.
  T3: Given a password of 13+ characters, registration succeeds.
```

During implementation, tests declare which points they cover:

```python
# Python — pytest marker
@pytest.mark.dhf_links("SRS-012")
@pytest.mark.dhf_testing("T1", "T2", "T3")
def test_password_length_validation():
    ...
```

```javascript
// JS/Jest — embedded tag in the test name
test("rejects short password @links:SRS-012 @testing:T1", () => { ... });
test("accepts 12-char password @links:SRS-012 @testing:T2", () => { ... });
```

When tests run with `--junit-xml`, these annotations are written as JUnit XML properties (`medharness.links`, `medharness.testing`). The CI gate checks them:

```bash
medharness ci test-points --dhf DHF --junit-dir test-results
```

This exits non-zero if any declared test point has no covering test, making gaps in test coverage visible before merge. Combined with `ci test-coverage` (requirement-level) and `ci dhf-validate` (schema and links), the three gates together enforce that every requirement is linked, every point is defined, and every point is tested.

## Incremental adoption

Nothing requires adopting everything at once. `medharness ci dhf-validate` is useful as a standalone CI gate well before any AI workflow is wired up — it catches broken traceability links and schema errors on every PR. Add `ci test-coverage` once you have test annotations. Add `ci test-points` once requirements include numbered testing fields. The AI phases (`generate-dhf`, `develop-cr`) can come later, or not at all if your team prefers manual design with automated validation. Each layer adds value independently.
