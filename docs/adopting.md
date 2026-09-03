# Adopting MedHarness

## Starting fresh

Run `medharness init` in an empty directory. You get a complete DHF scaffold with sample items, config, document templates, and plans. Four things to replace before your first real CR:

1. Items in `DHF/items/` — delete the sample YAML files and add your own (or leave samples while you learn the schema)
2. Plan documents in `DHF/documents/plans/` — fill in your project-specific plans (SDP, SMP, etc.)
3. `DHF/config/global.yaml` — set your project name
4. `AI-harness/context.md` — describe your product so Claude reasons about the right domain

Commit the result and start writing CRs. Document generation and traceability work against whatever items you have put in. CI is the one piece you add yourself — see [Setting up CI](#setting-up-ci).

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

What you do not need to migrate: test code (it stays in pytest, linked to DHF items via `medharness.links` annotations in JUnit output), generated documents (they are produced from items on demand), and CI scripts (start from the recipe in [Setting up CI](#setting-up-ci)). Migration is writing YAML files. The schema is self-documenting — look at the sample items from `init` to see every field and its expected values.

Traceability links between items are typed fields on child items (`derives_from`, `satisfies`, `implements`, `mitigates`, etc.). Run `medharness --dhf DHF verify dhf` at any point to check link integrity. The validator names the exact item, field, and target for every broken link.

### What blocks a build, and what only warns

`verify dhf` separates broken references from incomplete design, because the two need different fixes:

| Finding | Blocks? | Meaning |
|---------|---------|---------|
| Schema error | Always | An item does not match its doc-type schema |
| Required-traceability failure | Always | An item type that must have a parent link has none |
| **Dangling link** | Always | A link exists but its target ID does not — usually a typo or a deleted item |
| Coverage gap | Only with `--fail-on-uncovered` | An item has no downstream child yet — normal mid-project |

A dangling link is reported on its own rather than as a coverage gap. `SRS-001` pointing at a nonexistent `SYS-999` would otherwise show up only as "SYS→SRS 0/1 covered", and the remediation for that ("add a link") does not apply — the link is already there, it just resolves to nothing:

```
FAIL [dangling] RCM-001.mitigates → RISK-404: target does not exist
    Fix: correct the ID in RCM-001.yaml, or create RISK-404. The link exists but resolves to nothing.
```

Coverage gaps print as `WARN [coverage]` and leave the exit code at zero unless you pass `--fail-on-uncovered`. The recommended pipeline in [Setting up CI](#setting-up-ci) passes it. If you are backfilling an existing DHF and want the other checks green while you work through the gaps, drop the flag and add it back when the backlog is clear.

## Using dhfkit standalone

`dhfkit` is the DHF engine inside MedHarness — it ships as part of the same package (`pip install medharness`), not as a separate PyPI distribution. If your team has its own orchestration and only needs the engine layer — item storage, traceability graphs, lifecycle transitions, document generation — you can import from `dhfkit` directly and ignore the `medharness` CLI harness and AI workflow entirely. It has no dependency on the verification commands or prompt assembly layer. The `LocalDHFAdapter` gives programmatic access to items; the document generation pipeline is available separately. This is the right entry point for teams integrating DHF tooling into an existing CI system rather than adopting the full CR workflow.

## Software safety classification

IEC 62304 §4.3 asks every project to classify its software, and the class decides which activities the standard requires at all — architectural design, detailed design, integration testing, and system testing are not demanded of every class.

Declare it in `DHF/config/global.yaml`:

```yaml
software_safety_class: "B"      # A | B | C
classification_rationale: >
  Failure can contribute to a hazardous situation resulting in
  non-serious injury. Segregation of the reporting module is
  documented in SYSARCH-004.
```

| Class | Meaning |
|-------|---------|
| A | No injury or damage to health is possible |
| B | Non-serious injury is possible |
| C | Death or serious injury is possible |

```bash
medharness --dhf DHF verify classification
medharness --dhf DHF verify plans
```

### The activity map is yours

`DHF/config/safety_activities.yaml` maps each class to the items, plans, and test levels it requires. It ships with a documented default **and is meant to be edited**: assessors differ on how the §5 activity table reads, and your regulatory strategy may reasonably require more than the minimum. The file lives in the DHF, so your interpretation is recorded beside the evidence it governs.

Some things the standard fixes regardless, and the file does not override: risk management (§7, ISO 14971), release (§5.8), configuration management (§8), and problem resolution (§9) apply to every class.

### Per-module classification

§4.3(b) permits a software item to carry a lower class than the system where segregation is documented. MODULE items accept it:

```yaml
id: MODULE-004
safety_class: A
segregation_rationale: >
  Runs in a separate process with no shared state; separation is
  described in SYSARCH-001.
```

An override without a rationale is reported as a warning rather than an error — the justification may legitimately live in the architecture rather than on the item.

### Adoption is opt-in

A DHF with no declared class warns and exits zero, and the class-dependent checks (`verify plans`, and verification levels in `verify tests`) stay inactive. Nothing that passes today starts failing because this exists.

Once you declare one, `verify classification` requires `DHF/config/safety_activities.yaml` to define activities for that class. A project that adopted MedHarness before the file existed can obtain it with `medharness upgrade --apply`; it is project-owned from then on, and upgrade will never overwrite your edits.

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
medharness --dhf DHF verify tests --junit-dir test-results
```

### Verification levels

IEC 62304 asks for integration testing (§5.6) and system testing (§5.7) as records distinct from unit verification (§5.5). Declare the level a test provides:

```python
@pytest.mark.dhf_links("SRS-012")
@pytest.mark.dhf_level("integration")
def test_password_policy_enforced_end_to_end():
    ...
```

The level travels as a JUnit property (`medharness.level`) rather than being inferred from a directory, so a results file copied between CI jobs keeps saying what it is.

Once a [safety class](#software-safety-classification) is declared, `verify tests` requires the levels that class demands. A requirement verified only by unit tests then reports:

```
FAIL [test-level] SRS-012: verified at unit but missing integration, system
      Fix: mark a covering test with @pytest.mark.dhf_level("integration"), or
           set the medharness.level JUnit property.
```

**Unlabelled tests count as unit**, which is what they were already being counted as — existing suites keep working, and the requirement only applies once a class demanding it is declared.

Which levels a class demands can differ by requirement type — §5.5 unit verification, §5.6 integration testing and §5.7 system testing do not verify the same artefact. In `safety_activities.yaml`, a list applies to every type while a mapping applies per type:

```yaml
required_test_levels:
  SRS: [unit, integration]
  SYS: [system]
```

A type the mapping omits requires no level. Which clause covers which artefact depends on how your project defines SYS against SRS, so the shipped defaults are a starting point rather than a ruling — the file is yours, and `upgrade` will not overwrite it.

This exits non-zero if a requirement lacks coverage or if any declared test point has no covering test, making gaps in test coverage visible before merge. Combined with `verify dhf` (schema and links), it enforces that requirements are linked and verified before merge.

## AI-assisted CR workflow

MedHarness can drive the full design-to-code cycle for a change request. The workflow is optional — each step is a separate CLI command you can run manually or wire into CI.

### `change plan` — design phase

```bash
medharness --dhf DHF change plan --cr CR-001
```

Runs triage, then generates the V-model DHF item cascade (CRS → SYS → SRS → SWDD), then writes an implementation plan into `implementation_notes` on the CR item. On completion the CR item carries:

| Field | Written by | Required at closure |
|-------|-----------|-------------------|
| `triage_result` | Step 1 (triage) | ✓ verdict must be `approved` |
| `affected_risk_items` | Step 2.5 (risk impact) | ✓ explicit list (can be `[]`) |
| `implementation_notes` | Step 3 (impl plan) | ✓ non-empty |
| `proposed_new_items` | Step 4 (artifact record) | ✓ list of created items |

### `change implement` — development phase

```bash
medharness --dhf DHF change implement --cr CR-001
```

Reads `implementation_notes` as the primary spec and implements the code, annotates tests with `@links:<ITEM_ID>`, and runs a code review loop.

### `verify completion` — closure gate

```bash
medharness --dhf DHF verify completion --cr CR-001 --junit-dir test-results
```

Run after the branch is merged. Checks:

1. All four CR fields above are populated.
2. A design review file exists at `docs/reviews/<CR>-Design-Review.md` with `**Verdict:** Approved`.
3. Every item listed in `proposed_new_items` exists in the DHF.
4. All created verifiable items (CRS, SYS, SRS) have `verification_method` set.
5. Items with `Test` method have passing JUnit evidence.

Exits non-zero and prints `FAIL [cr-complete]` lines for each gap.

## Syncing SOUP items from dependency manifests (`dhfkit soup-sync`)

The `soup-sync` command reads dependency files from your project and creates or updates SOUP items in the DHF. It supports nine lockfile/manifest formats across multiple ecosystems:

| File | Ecosystem |
|------|-----------|
| `requirements.txt` | PyPI (pinned `==` only) |
| `uv.lock` | PyPI |
| `poetry.lock` | PyPI |
| `pyproject.toml` | PyPI (best-effort; prefer lockfile) |
| `package.json` | npm |
| `package-lock.json` | npm (v1/v2/v3) |
| `go.mod` | Go |
| `Cargo.lock` | crates.io |
| `pom.xml` | Maven |

### Auto-discovery

With no flags, `soup-sync` looks for the supported files in the project root automatically:

```bash
dhfkit --dhf DHF soup-sync
```

To target a specific file:

```bash
dhfkit --dhf DHF soup-sync --manifest uv.lock
dhfkit --dhf DHF soup-sync --manifest go.mod --manifest Cargo.lock
```

### Persistent source configuration (`soup-sources.yaml`)

For projects with non-standard layouts, multiple manifests, hardware SOUP, or third-party scanning tools, create `DHF/config/soup-sources.yaml`. This file is checked by default whenever no `--manifest` flags are given:

```yaml
sources:
  # Manifest files — paths relative to project root
  - type: manifest
    path: backend/requirements.txt

  - type: manifest
    path: frontend/package-lock.json

  # External tool — stdout must be NDJSON: {"name":…,"version":…,"ecosystem":…}
  - type: command
    run: "syft . -o syft-json=- | python3 -c \"
      import sys,json
      for a in json.load(sys.stdin)['artifacts']:
          print(json.dumps({'name':a['name'],'version':a['version'],'ecosystem':a['type']}))
      \""

  # Manual entries — hardware, OS, commercial tools (no ecosystem = no CVE scan)
  - type: manual
    items:
      - name: Ubuntu Server
        version: "22.04.3 LTS"
        manufacturer: Canonical Ltd.
        license: GPL-2.0
        ecosystem: null
      - name: PostgreSQL
        version: "14.10"
        manufacturer: PostgreSQL Global Development Group
        ecosystem: null
```

Source priority when multiple are configured: explicit `--manifest` flags → `--from-command` flags → `soup-sources.yaml` → auto-discovery.

### Applying changes

By default `soup-sync` prints a diff and exits. Pass `--write` to create and update SOUP items:

```bash
dhfkit --dhf DHF soup-sync --write
dhfkit --dhf DHF soup-sync --write --manifest uv.lock --cr CR-042
```

## SOUP vulnerability scanning (`verify soup`)

SOUP items that carry an `ecosystem` field (e.g. `PyPI`, `npm`, `Go`) are checked against the [OSV vulnerability database](https://osv.dev) on every run:

```bash
medharness --dhf DHF verify soup
```

Add the `ecosystem` field to each SOUP item to enable scanning:

```yaml
id: SOUP-012
name: requests
version: "2.28.2"
ecosystem: PyPI     # enables CVE scanning via osv.dev
manufacturer: Python Software Foundation
purpose: HTTP client for REST API calls
```

Items without `ecosystem` are skipped with a note. The command exits non-zero if any unresolved vulnerabilities are found and outputs structured JSON to stdout. Wire it into CI after `verify dhf` to catch unresolved CVEs before release.

### Accepting a vulnerability you have assessed

IEC 62304 §8.1.2 requires SOUP anomalies to be *evaluated* — not necessarily fixed. Many CVEs do not affect how your product uses the package, and some have no upstream patch. Record the assessment on the SOUP item and the gate stops blocking on it:

```yaml
id: SOUP-012
name: requests
version: "2.28.2"
ecosystem: PyPI
accepted_vulns:
  - id: GHSA-x84v-xcm2-53pg
    rationale: "Affected redirect handling is not reachable — we never follow cross-host redirects. Assessed in CR-018."
```

Both keys are required. An entry without a `rationale` — or a bare ID string — is reported as a warning and the vulnerability **keeps blocking**, because an acceptance with no recorded reason is not an assessment.

Acceptance is per-vulnerability-ID by design. A newly published CVE against the same package still fails the gate, so blanket suppression cannot silently absorb future findings. `verify soup` prints accepted entries as `ACCEPTED [soup-vuln]` lines and includes them in its JSON output, so they stay visible in CI logs and evidence bundles.

### Air-gapped and proxy-restricted pipelines

`verify soup` calls `api.osv.dev`. Where that host is unreachable, the gate fails by default rather than passing silently. If your SOUP scanning happens through a separate offline process, tolerate the outage explicitly:

```bash
medharness --dhf DHF verify soup --offline-mode warn
```

The gate then passes, but still records the outage in its JSON output and prints a `WARN [soup-vuln]` line — so the gap is visible in the evidence bundle rather than invisible. Keep the default (`--offline-mode fail`) anywhere the scan is expected to run.

## Keeping your scaffold up to date (`upgrade`)

When a new MedHarness version ships, CI workflows, AI prompts, and spec templates may change. The `upgrade` command shows what's drifted and optionally applies the updates:

```bash
medharness upgrade                      # report only — exits non-zero if outdated
medharness upgrade --apply              # apply updates from the installed version
medharness upgrade --project-dir /path  # specify project root (default: cwd)
```

Files that are always **user-owned** (never modified by upgrade): `DHF/items/`, `DHF/config/global.yaml`, `AI-harness/context.md`, `CLAUDE.md`, and your CI workflow.

Files that upgrade manages: AI prompts (`.github/prompts/`), spec Jinja2 templates (`DHF/documents/specs/`), doc-type configs (`DHF/config/doc_types/`).

Your CI workflow is deliberately not managed — it is not part of the release payload, so `upgrade` has no template to compare against. When the recommended pipeline changes, the changelog says so and [Setting up CI](#setting-up-ci) carries the current recipe.

## Setting up CI

MedHarness does not install a CI workflow, and [docs/interface.md](interface.md) is the contract to build one against — the result shape every gate returns, exit-code semantics, and what may change. `medharness gates` lists the gates with what each requires and whether it blocks.

MedHarness does not install a CI workflow. The pipeline is yours to own — it references your branch names, runner labels, and secrets, and `medharness upgrade` will never overwrite it.

Create `.github/workflows/dhf.yml` with the recipe below, replacing `{{medharness_version}}` with the version you pinned in step one.

<details>
<summary><code>.github/workflows/dhf.yml</code></summary>

```yaml
name: DHF

on:
  pull_request:
    paths:
      - 'DHF/**'
  push:
    branches:
      - main
    tags:
      - 'v*'

jobs:
  dhf-validate:
    name: Validate DHF
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install medharness=={{medharness_version}}

      # --fail-on-uncovered makes a requirement with no downstream design or test
      # block the build. Drop the flag while backfilling an existing DHF; coverage
      # gaps then report as WARN and only schema, required links, and dangling
      # links block.
      - name: Schema and traceability check
        run: medharness verify dhf --dhf DHF --fail-on-uncovered

  evidence-bundle:
    name: Evidence bundle
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: dhf-validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install medharness=={{medharness_version}}

      - name: Build evidence bundle
        run: medharness evidence bundle --dhf DHF --out-dir artifacts

      - uses: actions/upload-artifact@v4
        with:
          name: dhf-evidence
          path: artifacts/

  release-baseline:
    name: Release Baseline
    if: startsWith(github.ref, 'refs/tags/v')
    needs: dhf-validate
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install medharness=={{medharness_version}}

      - name: Extract version from tag
        id: ver
        run: echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

      - name: Build release baseline
        run: |
          dhfkit --dhf DHF release-baseline \
            --version ${{ steps.ver.outputs.version }} \
            --out-dir artifacts \
            --write \
            --author "github-actions[bot]"

      - name: Commit REL item
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add DHF/
          git diff --cached --quiet || \
            git commit -m "ci: release baseline ${{ steps.ver.outputs.version }}" && \
            git push origin HEAD:main

      - uses: actions/upload-artifact@v4
        with:
          name: release-baseline-${{ steps.ver.outputs.version }}
          path: artifacts/
```

</details>

What each job does:

| Job | Trigger | Purpose |
|-----|---------|---------|
| `dhf-validate` | PRs touching `DHF/**`, pushes to `main` | Schema, required links, dangling links, coverage |
| `evidence-bundle` | Merge to `main` | Produces the runtime evidence artifact |
| `release-baseline` | `v*` tags | Writes the REL item and software BOM back to `main` |

Adopt it incrementally: `dhf-validate` alone is useful from day one. Add the other two when you need release artifacts.

## Incremental adoption

Nothing requires adopting everything at once. `medharness --dhf DHF verify dhf` is useful as a standalone CI gate well before any AI workflow is wired up — it catches broken traceability links and schema errors on every PR. Add `verify tests` once you have test annotations. If requirements include numbered testing fields, the same gate also enforces those test points. The AI phases (`change plan`, `change implement`) can come later, or not at all if your team prefers manual design with automated validation. Each layer adds value independently.
