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

If your team has its own orchestration and only needs the DHF engine — item storage, traceability graphs, lifecycle transitions, document generation — `dhfkit` works without the `medharness` CLI harness or AI workflow. Install with `pip install medharness` (dhfkit is bundled) and import from `dhfkit` directly. It has no dependency on the CI gates or prompt assembly layer. The `LocalDHFAdapter` gives programmatic access to items; the document generation pipeline is available separately. This is the right entry point for teams integrating DHF tooling into an existing CI system rather than adopting the full CR workflow.

## Incremental adoption

Nothing requires adopting everything at once. `medharness ci dhf-validate` is useful as a standalone CI gate well before any AI workflow is wired up — it catches broken traceability links and schema errors on every PR. Add `ci test-coverage` once you have test annotations. The AI phases (`generate-dhf`, `develop-cr`) can come later, or not at all if your team prefers manual design with automated validation. Each layer adds value independently.
