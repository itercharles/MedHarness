# Adopting MedHarness

How to take MedHarness into a project, and where each part is documented.

| You want to | Read |
|---|---|
| Add the CI gates, or cut a release | [CI and releases](ci.md) |
| Let an agent plan and write a change, with your own agent or unattended in CI | [The AI-assisted CR workflow](ai-workflow.md) |
| Keep the SOUP register, an SBOM and vulnerability checks | [SOUP, SBOM and vulnerabilities](soup.md) |
| Change a default, or add a type or a relationship | [Configuration](configuration.md) |
| Look up a command, its options or its answer | [interface.md](interface.md) |

## Starting fresh

Run `medharness init` as in the [README](../README.md#quick-start). Then replace:

| Replace | Why |
|---------|-----|
| `DHF/items/` | Delete the sample YAML and add your own, or keep them while you learn the schema |
| `DHF/config/global.yaml` | Check the project name. Anything else you set here overrides a default — see [Changing the defaults](configuration.md#changing-the-defaults) |
| `AGENTS.md` | Describe the product, so every coding agent — and the AI stages — reason about your domain |

CI is the one piece you add yourself, and it is the whole deployment.

## Bringing an existing DHF

MedHarness stores DHF content as YAML items, one file per record. The types and
the links between them are listed in the `DHF/README.md` that `init` writes.

Artifacts from common sources map directly to item types. A requirements spreadsheet becomes SRS and SYS items — one row per item, with `title` and `content` fields. A risk register becomes RISK items paired with RCM items (each RCM carries a `mitigates` field pointing to the RISK ID it controls). A SOUP list becomes SOUP items with `name`, `version`, and `purpose` fields.

What you do not need to migrate: test code (it stays in pytest, linked to DHF items via `medharness.links` annotations in JUnit output), generated documents (`build release` renders them from the items), and CI scripts (start from the recipe in [Setting up CI](ci.md#setting-up-ci)). Migration is writing YAML files. The schema is self-documenting — look at the sample items from `init` to see every field and its expected values.

Traceability links between items are typed fields on child items (`derives_from`, `satisfies`, `implements`, `mitigates`, etc.). Run `medharness --dhf DHF verify dhf` at any point to check link integrity. The validator names the exact item, field, and target for every broken link.

Which findings block a build and which only warn is in
[interface.md](interface.md#what-blocks-a-build). While backfilling, leave
`--strict` off: coverage gaps then warn, and schema, required links
and dangling links still fail.

### Change requests you already have

A DHF that kept change requests before MedHarness's closure criteria existed has two things to settle once, before its first release.

**A status that is no state of the type.** A CR written as `implementing` fails `verify dhf`: a CR's states are `new`, `design`, `develop`, `completed`, `rejected` and `cancelled`. Set each to what it really is — `develop` for work in flight, `completed` or `cancelled` for work that finished or stopped:

```bash
medharness --dhf DHF item update CR-004 --data '{"status": "develop"}'
```

**Completed CRs that never recorded their closure.** `build release` re-runs `verify completion` for every completed CR it includes, by default every completed CR not yet in a release, so CRs closed before `implementation_notes`, `affected_items` and `triage_result` existed fail it. Do not backfill those fields: a triage approval written years later is not a record of anything. Baseline the history instead. A REL item that lists those CRs in `included_items` takes them out of the default, and the decision is a reviewable change in your DHF:

```bash
medharness --dhf DHF item create --type REL --data '{"title": "Baseline of change requests completed before closure records", "version": "baseline", "included_items": ["CR-003", "CR-005"], "release_notes": "Completed before the closure criteria existed; accepted as they are."}'
```

CRs completed from then on carry the closure fields, and the next `build release` includes only them.

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

Under pytest with `--junit-xml`, the markers become JUnit properties (`medharness.links`, `medharness.testing`); other runners carry the tags in the test name. The CI gate reads either:

```bash
medharness --dhf DHF verify tests --junit test-results
```

This exits non-zero if a requirement lacks coverage or if any declared test point has no covering test, making gaps in test coverage visible before merge. Combined with `verify dhf` (schema and links), it enforces that requirements are linked and verified before merge.

## What to adopt, in what order

Start with the AI development, and add the checks that make it trustworthy. Each
step is useful on its own.

| Step | Add | Needs |
|------|-----|-------|
| 1 | Your coding agent follows the process: `init` writes `AGENTS.md`, and the agent runs `build plan --prompt` and `build code --prompt` | A coding agent you already use. No key, nothing in CI |
| 2 | `verify dhf` as a PR gate | Nothing — works on day one. It is what checks the design the agent wrote |
| 3 | Unattended AI in CI: `build plan` and `build code` from an issue | An AI key, an ephemeral runner, and branch protection that requires an approving review. Put it behind step 2 |
| 4 | `verify tests` | Test annotations in JUnit output |
| 5 | `build soup`, `verify soup` | A dependency manifest |
| 6 | `build release` on version tags | Steps 2, 4 and 5 passing |

Steps 1 and 3 are optional in the strong sense: a team that writes its DHF by hand
starts at step 2 and loses nothing the standard asks for.
