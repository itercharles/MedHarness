# Adopting MedHarness

## Starting fresh

```bash
pip install medharness
medharness init            # in a directory with no DHF/ yet
```

You get a DHF with sample items, its config, document templates, and a
`CLAUDE.md`. Three things to replace before your first real CR:

| Replace | Why |
|---------|-----|
| `DHF/items/` | Delete the sample YAML and add your own, or keep them while you learn the schema |
| `DHF/config/global.yaml` | Check the project name; adjust `required_traceability` if your V-model differs |
| `CLAUDE.md` | Describe the product, so the AI stages reason about your domain |

Check it at any point:

```bash
medharness verify dhf
```

Document generation and traceability work against whatever items you have put in. CI is the one piece you add yourself — [Setting up CI](#setting-up-ci) is next, and is the whole deployment.

## Setting up CI

`init` does not write a CI workflow, because the pipeline references your branch names, runner labels and secrets. You own it, and `upgrade` will never touch it.

Copy the recipe below into `.github/workflows/dhf.yml` and replace `{{medharness_version}}` with the version you pin. It is the whole deployment — two jobs, no server, no database, no account:

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
        run: medharness --dhf DHF verify dhf --fail-on-uncovered

  release:
    name: Release
    if: startsWith(github.ref, 'refs/tags/v')
    needs: dhf-validate
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
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

      - name: Build the release
        run: |
          medharness --dhf DHF build release \
            --version ${{ steps.ver.outputs.version }} \
            --out-dir artifacts \
            --write

      # Through a pull request, not a push to main: a branch protection rule
      # requiring review is the normal configuration for a controlled repo, and
      # a REL item is a DHF record like any other.
      - name: Open a pull request for the REL item
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          VERSION: ${{ steps.ver.outputs.version }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add DHF/
          if git diff --cached --quiet; then
            echo "No DHF change to record for $VERSION."
            exit 0
          fi
          BRANCH="chore/release-$VERSION"
          git checkout -b "$BRANCH"
          git commit -m "ci: release $VERSION"
          git push origin "$BRANCH"
          gh pr create --base main --head "$BRANCH" \
            --title "ci: release $VERSION" \
            --body "REL item and software BOM for version $VERSION, written by the release job. Artifacts are attached to the workflow run."

      - uses: actions/upload-artifact@v4
        with:
          name: release-${{ steps.ver.outputs.version }}
          path: artifacts/
```

</details>

What each job does:

| Job | Trigger | Purpose |
|-----|---------|---------|
| `dhf-validate` | PRs touching `DHF/**`, pushes to `main` | Schema, required links, dangling links, coverage |
| `release` | `v*` tags | Runs `build release`: the baseline, BOM, SBOM and evidence bundle as a workflow artifact, and the REL item back to `main` through a pull request |

Adopt it incrementally: `dhf-validate` alone is useful from day one. Add `release` when you start cutting versions. Evidence is produced once per release, not on every merge.

Writing your own pipeline instead? [interface.md](interface.md) is the contract — the result shape every gate returns, exit-code semantics, and what may change between versions.

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

This exits non-zero if a requirement lacks coverage or if any declared test point has no covering test, making gaps in test coverage visible before merge. Combined with `verify dhf` (schema and links), it enforces that requirements are linked and verified before merge.

## AI-assisted CR workflow

MedHarness can drive the full design-to-code cycle for a change request. The workflow is optional — each step is a separate CLI command you can run manually or wire into CI.

### `build plan` — design phase

```bash
medharness --dhf DHF build plan --cr CR-001
```

Runs triage, then generates the V-model DHF item cascade (CRS → SYS → SRS → SWDD), then writes an implementation plan into `implementation_notes` on the CR item. On completion the CR item carries:

| Field | Written by | Required at closure |
|-------|-----------|-------------------|
| `triage_result` | Step 1 (triage) | ✓ verdict must be `approved` |
| `affected_risk_items` | Step 2.5 (risk impact) | ✓ explicit list (can be `[]`) |
| `implementation_notes` | Step 3 (impl plan) | ✓ non-empty |
| `proposed_new_items` | Step 4 (artifact record) | ✓ list of created items |

### `build code` — development phase

```bash
medharness --dhf DHF build code --cr CR-001
```

Reads `implementation_notes` as the primary spec and implements the code, annotates tests with `@links:<ITEM_ID>`, and runs a code review loop.

### `verify completion` — closure gate

```bash
medharness --dhf DHF verify completion --cr CR-001 --junit-dir test-results
```

Run it on the branch to block the merge, and again on `main`, where the tests re-run against whatever else landed. Checks, for the items this CR touched only:

1. All four CR fields above are populated.
2. Every item listed in `proposed_new_items` exists in the DHF.
3. All created verifiable items (CRS, SYS, SRS) have `verification_method` set.
4. Items with `Test` method have passing JUnit evidence.

Approval is not its question — that is `workflow check-approval`, which reads the pull request's reviews. Exits non-zero and prints `FAIL [cr-complete]` lines for each gap.

## Syncing SOUP items from dependency manifests (`medharness build dhf`)

The `build dhf` command reads dependency files from your project and creates or updates SOUP items in the DHF. It supports nine lockfile/manifest formats across multiple ecosystems:

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

With no flags, `build dhf` looks for the supported files in the project root automatically:

```bash
medharness --dhf DHF build dhf
```

To target a specific file:

```bash
medharness --dhf DHF build dhf --manifest uv.lock
medharness --dhf DHF build dhf --manifest go.mod --manifest Cargo.lock
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

By default `build dhf` prints a diff and exits. Pass `--write` to create and update SOUP items:

```bash
medharness --dhf DHF build dhf --write
medharness --dhf DHF build dhf --write --manifest uv.lock
```

## Exporting an SBOM (`dhfkit sbom`)

The SOUP register already holds what an SBOM needs — name, version, ecosystem,
licence, supplier — recorded there because IEC 62304 §8.1.2 asks for it. FDA's
premarket cybersecurity guidance and the EU Cyber Resilience Act want that in a
standard machine-readable format:

```bash
dhfkit --dhf DHF sbom                      # writes DHF/sbom.cdx.json
dhfkit --dhf DHF sbom --output build/sbom.cdx.json
dhfkit --dhf DHF sbom --stdout             # for a pipeline
```

The output is CycloneDX 1.6 JSON, checked against the official schema by the
test suite rather than by assertion. Each component carries its SOUP id as
`bom-ref` and as a `dhfkit:soup_id` property, so a finding in the SBOM leads back
to the DHF item holding the justification and any documented vulnerability
acceptance.

**A component gets no `purl` when one cannot be built honestly**, and the command
names the reason per component. Two causes need different fixes:

- the ecosystem has no package-URL type — the mapping is a fixed table;
- the version is a range (`^34.15.1`) rather than a version. §8.1.2 wants the
  version actually in use, and a purl built from a range resolves against a real
  registry and matches nothing.

The component is still listed either way, and its `version` is reported exactly as
the DHF records it — the SBOM does not clean up the register's data. A wrong purl resolves against a real
registry, so an absent one is safer than a guessed one. The mapped ecosystems are
PyPI, npm, Go, Maven, crates.io, NuGet, RubyGems, Packagist, Hex and Pub.

Regenerating an unchanged SBOM leaves the file alone, timestamp included — the
serial number is derived from the component set rather than randomised, so a
regeneration is not a diff in a repository whose purpose is showing what changed.

`build release` writes one too, alongside the rest of the release:

```
release/release-baseline.json
release/software-bom.json      # dhfkit's own shape, unchanged
release/sbom.cdx.json          # the same release in CycloneDX
release/evidence-manifest.json # every file above and below, hashed
release/specifications/ …      # plus traceability and test evidence
```

`--manifest` accepts every format `build dhf` reads — `requirements.txt`, `uv.lock`, `poetry.lock`, `pyproject.toml`, `package.json`, `package-lock.json`, `go.mod`, `Cargo.lock`, `pom.xml`.

The release SBOM merges both registers. A package read from a `--manifest` but
absent from the SOUP register still ships, so it appears — carrying a
`dhfkit:manifest_source` property instead of a `dhfkit:soup_id`. Leaving it out
would understate the release and hide the §8.1.2 gap `build dhf` exists to close.
Where a package is in both, the SOUP item wins: it carries the licence, supplier
and any documented vulnerability acceptance that the manifest does not.

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

## Cutting a release (`build release`)

```bash
medharness --dhf DHF build release --version 1.2.0 --out-dir release --junit-dir test-results
```

One command builds everything a release needs, into one directory: the release baseline, the software BOM, a CycloneDX SBOM, the specifications, traceability matrices, test evidence, and `evidence-manifest.json` hashing every file.

Before writing anything to the DHF it checks that:

- the DHF passes `verify dhf` — with coverage gaps failing, since a release is not the place for advisory findings;
- every included CR is `completed` (by default, every completed CR not yet in a release; `--cr` to choose);
- every open defect carries a `release_rationale` (IEC 62304 §9.7).

Add `--write` to record the REL item. It is recorded **only when every check passed** — a failing release still writes its evidence, so you can read why, but leaves the DHF unchanged. The [CI recipe](#setting-up-ci) runs it on `v*` tags and brings the REL item back to `main` through a pull request.

## Keeping your scaffold up to date (`upgrade`)

When a new MedHarness version ships, CI workflows, AI prompts, and spec templates may change. The `upgrade` command shows what's drifted and optionally applies the updates:

```bash
medharness upgrade                      # report only — exits non-zero if outdated
medharness upgrade --apply              # apply updates from the installed version
medharness upgrade --project-dir /path  # specify project root (default: cwd)
```

Files that are always **yours** (never modified by upgrade): `DHF/items/`, `DHF/config/global.yaml`, `DHF/config/soup-sources.yaml` once it exists, `DHF/README.md`, `CLAUDE.md`, and your CI workflow.

Files that upgrade manages: doc-type configs (`DHF/config/doc_types/`) and the spec templates (`DHF/documents/specs/`).

Your CI workflow is deliberately not managed — it is not part of the release payload, so `upgrade` has no template to compare against. When the recommended pipeline changes, the changelog says so and [Setting up CI](#setting-up-ci) carries the current recipe.

## Using dhfkit standalone

`dhfkit` is the storage engine inside MedHarness. It ships in the same package (`pip install medharness`), not as a separate distribution, and has no dependency on the harness — so a team with its own orchestration can import it directly and ignore the CLI harness and AI workflow.

What it gives you: item storage and retrieval, schemas, lifecycle transitions, document generation, and a CycloneDX SBOM. SOUP sync (`build dhf`) and releases (`build release`) are `medharness`. `LocalDHFAdapter` is the programmatic entry point.

What it does not give you: **traceability analysis**. Coverage, required links, cycles and risk chains live in `medharness`, which reads the same YAML items. Requirements kept in another system are checked by exporting them into `DHF/items/` in this format. See [architecture.md](architecture.md).

## What to adopt, in what order

Each layer is useful on its own. None requires the next.

| Step | Add | Needs |
|------|-----|-------|
| 1 | `verify dhf` as a PR gate | Nothing — works on day one |
| 2 | `verify tests` | Test annotations in JUnit output |
| 3 | `build dhf`, `sbom`, `verify soup` | A dependency manifest |
| 4 | `build release` on version tags | Steps 1–3 passing |
| 5 | `build plan` / `build code` | An AI key, and the appetite for it |

Step 5 is optional in the strong sense: teams that prefer manual design with automated validation stop at step 4 and lose nothing the standard asks for.
