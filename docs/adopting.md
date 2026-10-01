# Adopting MedHarness

## Starting fresh

Run `medharness init` as in the [README](../README.md#quick-start). Then replace:

| Replace | Why |
|---------|-----|
| `DHF/items/` | Delete the sample YAML and add your own, or keep them while you learn the schema |
| `DHF/config/global.yaml` | Check the project name. Anything else you set here overrides a default — see [Changing the defaults](#changing-the-defaults) |
| `AGENTS.md` | Describe the product, so every coding agent — and the AI stages — reason about your domain |

CI is the one piece you add yourself, and it is the whole deployment.

## Setting up CI

`init` does not write a CI workflow, because the pipeline references your branch names, runner labels and secrets. You own it.

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

      # --strict makes a requirement with no downstream design or test
      # block the build. Drop the flag while backfilling an existing DHF; coverage
      # gaps then report as WARN and only schema, required links, and dangling
      # links block.
      - name: Schema and traceability check
        run: medharness --dhf DHF verify dhf --strict

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

MedHarness stores DHF content as YAML items, one file per record. The types and
the links between them are listed in the `DHF/README.md` that `init` writes.

Artifacts from common sources map directly to item types. A requirements spreadsheet becomes SRS and SYS items — one row per item, with `title` and `content` fields. A risk register becomes RISK items paired with RCM items (each RCM carries a `mitigates` field pointing to the RISK ID it controls). A SOUP list becomes SOUP items with `name`, `version`, and `purpose` fields.

What you do not need to migrate: test code (it stays in pytest, linked to DHF items via `medharness.links` annotations in JUnit output), generated documents (`build release` renders them from the items), and CI scripts (start from the recipe in [Setting up CI](#setting-up-ci)). Migration is writing YAML files. The schema is self-documenting — look at the sample items from `init` to see every field and its expected values.

Traceability links between items are typed fields on child items (`derives_from`, `satisfies`, `implements`, `mitigates`, etc.). Run `medharness --dhf DHF verify dhf` at any point to check link integrity. The validator names the exact item, field, and target for every broken link.

Which findings block a build and which only warn is in
[interface.md](interface.md#what-blocks-a-build). While backfilling, leave
`--strict` off: coverage gaps then warn, and schema, required links
and dangling links still fail.

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

## AI-assisted CR workflow

MedHarness can drive the full design-to-code cycle for a change request. The workflow is optional — each step is a separate CLI command you can run manually or wire into CI.

### With the coding agent you already use

`--prompt` on `build plan` and `build code` prints the stage — its steps and
this CR's DHF context, exactly what the CI agent is given — for an agent that is
already running, and starts nothing. `init` writes this section into
`AGENTS.md`, which most coding agents read, and a `CLAUDE.md` that imports it
for Claude Code. A project that predates it adds the section by hand:

```markdown
## Design History File

This repository keeps its Design History File in `DHF/`, checked by MedHarness.
A change to what the product does is not finished until its DHF is.

- **Start a change:** `medharness item create --type CR --data '{"title": "…", "description": "…"}'`,
  then `medharness item transition CR-NNN design`.
- **Design it:** run `medharness build plan --cr CR-NNN --prompt` and do what it says.
- **Build it:** run `medharness build code --cr CR-NNN --prompt` and do what it says.
- **Check it**, and fix what they report:
  - `medharness verify dhf`
  - `medharness verify completion --cr CR-NNN --junit <results>`
  - `medharness verify changes --cr CR-NNN`
- **Close it:** `medharness item transition CR-NNN completed`.

Go through `medharness item` for every DHF question and change, inside a CR or not:

- **Read** with `medharness item list --type <TYPE>` and `medharness item get <ID>`;
  `get` includes every ID the item links to.
- **Write** with `medharness item create|update|transition`, never by editing the
  files under `DHF/`: these check the schema before writing, allocate IDs, enforce
  the lifecycle, and change only the fields you pass.
- After any change, run `medharness verify dhf`.
```

Then ask your agent to "open a CR for the PDF export and update the DHF": it
creates the CR, runs `build plan --cr CR-015 --prompt`, and does what it says.

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
| `affected_items` | Step 4; in CI, `build plan` and `build code` rewrite it from the branch | ✓ explicit list (can be `[]`) |

### `build code` — development phase

```bash
medharness --dhf DHF build code --cr CR-001
```

Reads `implementation_notes` as the primary spec and implements the code, annotates tests with `@links:<ITEM_ID>`, and runs a code review loop.

The answer's `artifacts.files_changed` lists the code changed on the branch, committed or not: the whole repository except the DHF. Set `MEDHARNESS_CODE_PATHS` (comma-separated, e.g. `src/,lib/`) to narrow it.

### `verify completion` — closure gate

```bash
medharness --dhf DHF verify completion --cr CR-001 --junit test-results
```

Run it on the branch to block the merge, and again on `main`, where the tests re-run against whatever else landed. Checks, for the items this CR touched only:

1. All four CR fields above are populated. A CR planned by hand records them with `medharness item update`.
2. Every item in `affected_items` exists in the DHF.
3. Those that are requirements (CRS, SYS, SRS) or SOUP have `verification_method` set.
4. Those with `Test` have passing JUnit evidence.

Approval is not its question — GitHub's branch protection enforces that (required approvals, stale approvals dismissed on push). Exits non-zero and prints `FAIL [completion]` lines for each gap.

### Wiring it into GitHub Actions

MedHarness does not interpret GitHub events; the workflow's own `if:` does. A
sketch, with branches named `design/CR-NNN` and `develop/CR-NNN`:

```yaml
on:
  issues:
    types: [labeled]
  workflow_dispatch:
    inputs:
      cr:    { description: "CR ID, e.g. CR-012", required: true }
      stage: { type: choice, options: [plan, code], required: true }
  pull_request_review:
    types: [submitted]

jobs:
  intake:           # labelling an issue `cr` opens a CR from it and drafts the design
    if: github.event_name == 'issues' && github.event.label.name == 'cr'
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ github.token }}
      TITLE: ${{ github.event.issue.title }}
      BODY: ${{ github.event.issue.body }}
      ISSUE: ${{ github.event.issue.number }}
    steps:
      - uses: actions/checkout@v4
      - run: pip install medharness
      - run: |          # the issue text reaches the shell through env only, never ${{ }}
          DATA=$(jq -n --arg t "$TITLE" --arg d "$BODY" '{title: $t, description: $d}')
          CR=$(medharness item create --type CR --data "$DATA" | jq -r .id)
          medharness build plan --cr "$CR"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "design/$CR" && git add -A && git commit -m "design/$CR"
          git push origin "design/$CR"
          gh pr create --head "design/$CR" --title "$CR: $TITLE" --body "Closes #$ISSUE"

  start:            # a person starts a stage by hand; there is no PR yet
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ github.token }}
      BRANCH: ${{ inputs.stage == 'plan' && 'design' || 'develop' }}/${{ inputs.cr }}
    steps:
      - uses: actions/checkout@v4
      - run: pip install medharness
      - if: inputs.stage == 'plan'
        run: medharness build plan --cr "${{ inputs.cr }}"
      - if: inputs.stage == 'code'
        run: medharness build code --cr "${{ inputs.cr }}"
      - run: |          # without --pr the files changed and nothing was committed
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH" && git add -A && git commit -m "$BRANCH"
          git push origin "$BRANCH"
          gh pr create --head "$BRANCH" --title "$BRANCH" --body "Opened by the CR workflow."

  revise:           # a reviewer asked for changes on a stage's pull request
    if: github.event_name == 'pull_request_review' && github.event.review.state == 'changes_requested'
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ github.token }}
      BRANCH: ${{ github.event.pull_request.head.ref }}
      PR: ${{ github.event.pull_request.number }}
    steps:
      - uses: actions/checkout@v4
        with: { ref: "${{ github.event.pull_request.head.ref }}" }
      - run: pip install medharness
      - run: |          # --pr: revise from the reviews, then commit and push to the PR
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          case "${BRANCH%%/*}" in
            design)  medharness build plan --cr "${BRANCH#*/}" --pr "$PR" ;;
            develop) medharness build code --cr "${BRANCH#*/}" --pr "$PR" ;;
          esac
```

**An issue is the agent's instructions.** `intake` turns the issue's title and
body into the CR that `build plan` works from, so label only issues whose text
you would hand to an agent with a shell — adding a label already needs triage
access. PRs opened with `github.token` start no workflows, so give `gh pr create`
another token if the PR's own checks should run on it.

**`--pr` is CI; without it, local.** Without `--pr`, `build plan` and `build
code` change files in the working tree and commit nothing — at your desk, or in
a job that commits itself, like `start` above. With `--pr N` they revise when a
reviewer has asked for a change on the PR's current commit — an approval asks for
nothing — and commit and push the
result to its branch; the job needs git's user configured and a token that can
push. Either way the agent does not commit: if it does anyway — a repository's
`CLAUDE.md` may tell it to — its commits are undone, their changes kept, and the
answer carries an `agent_commits_undone` warning.

`artifacts.items_changed` and `artifacts.files_changed` are the branch against
`origin/main`, committed or not — the CR's whole change set across every run,
not what this run added. `build plan` records `items_changed` as the CR's
`affected_items`.

`build plan` and `build code` need the model's credentials in the job's
environment — see [ai-security.md](ai-security.md) before giving them to a
runner.


## Syncing SOUP items from dependency manifests (`medharness build soup`)

The `build soup` command reads dependency files from your project and creates or updates SOUP items in the DHF. It supports nine lockfile/manifest formats across multiple ecosystems:

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

With no flags, `build soup` looks for the supported files in the project root automatically:

```bash
medharness --dhf DHF build soup
```

To target a specific file:

```bash
medharness --dhf DHF build soup --manifest uv.lock
medharness --dhf DHF build soup --manifest go.mod --manifest Cargo.lock
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
    run: |
      syft . -o syft-json=- | python3 -c "
      import sys, json
      for a in json.load(sys.stdin)['artifacts']:
          print(json.dumps({'name': a['name'], 'version': a['version'], 'ecosystem': a['type']}))
      "

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

`build soup` creates and updates the SOUP items in the working tree, and commits
nothing; review the change with `git diff DHF/` before you commit it:

```bash
medharness --dhf DHF build soup
medharness --dhf DHF build soup --manifest uv.lock
```

## Exporting an SBOM

The SOUP register already holds what an SBOM needs — name, version, ecosystem,
licence, supplier — recorded there because IEC 62304 §8.1.2 asks for it. FDA's
premarket cybersecurity guidance and the EU Cyber Resilience Act want that in a
standard machine-readable format. `build release` writes it as
`sbom.cdx.json`, beside the specifications. Without `--write` the DHF is not
changed:

```bash
medharness build release --version 1.2.0 --out-dir release
```

The output is CycloneDX 1.6 JSON, checked against the official schema by the
test suite rather than by assertion. Each component carries its SOUP id as
`bom-ref` and as a `dhfkit:soup_id` property, so a finding in the SBOM leads back
to the DHF item holding the justification and any documented vulnerability
acceptance.

**A component gets no `purl` when one cannot be built honestly**, and the release
names the reason per component as a `WARN [release]` line and in its `warnings`. Two causes need different fixes:

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

Everything `build release` writes:

```
release/release-baseline.json
release/software-bom.json      # dhfkit's own shape, unchanged
release/sbom.cdx.json          # the same release in CycloneDX
release/evidence-manifest.json # every file above and below, hashed
release/specifications/ …      # plus traceability and test evidence
```

`--manifest` accepts every format `build soup` reads — `requirements.txt`, `uv.lock`, `poetry.lock`, `pyproject.toml`, `package.json`, `package-lock.json`, `go.mod`, `Cargo.lock`, `pom.xml`.

The release SBOM merges both registers. A package read from a `--manifest` but
absent from the SOUP register still ships, so it appears — carrying a
`dhfkit:manifest_source` property instead of a `dhfkit:soup_id`. Leaving it out
would understate the release and hide the §8.1.2 gap `build soup` exists to close.
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

Acceptance is per-vulnerability-ID by design. A newly published CVE against the same package still fails the gate, so blanket suppression cannot silently absorb future findings. `verify soup` prints accepted entries as `ACCEPTED [soup-vuln]` lines and lists them in the `warnings` of its answer, so they stay visible in CI logs and evidence bundles.

### Air-gapped and proxy-restricted pipelines

`verify soup` calls `api.osv.dev`. Where that host is unreachable, the gate fails by default rather than passing silently. If your SOUP scanning happens through a separate offline process, tolerate the outage explicitly:

```bash
medharness --dhf DHF verify soup --offline-mode warn
```

The gate then passes, but still records the outage in the `warnings` of its answer and prints a `WARN [soup-vuln]` line — so the gap is visible in the evidence bundle rather than invisible. Keep the default (`--offline-mode fail`) anywhere the scan is expected to run.

## Cutting a release (`build release`)

```bash
medharness --dhf DHF build release --version 1.2.0 --out-dir release --junit test-results
```

One command builds everything a release needs, into one directory: the release baseline, the software BOM, a CycloneDX SBOM, the specifications, a traceability report for each matrix in `traceability_matrices`, test evidence, and `evidence-manifest.json` hashing every file.

Before writing anything to the DHF it checks that:

- the DHF passes `verify dhf` — with coverage gaps failing, since a release is not the place for advisory findings;
- every included CR is `completed` (by default, every completed CR not yet in a release; `--cr` to choose) **and still passes `verify completion`** — `completed` is a status anyone can write, so the gate is run again, with the `--junit` evidence if you pass it. Without `--junit`, a Test-verified item's evidence cannot be checked, and the release says so in `warnings`;
- every open defect carries a `release_rationale` (IEC 62304 §9.7).

Add `--write` to record the REL item. It is recorded **only when every check passed** — a failing release still writes its evidence, so you can read why, but leaves the DHF unchanged. The [CI recipe](#setting-up-ci) runs it on `v*` tags and brings the REL item back to `main` through a pull request.

## Changing the defaults

MedHarness reads two layers. The **defaults** ship inside the package: 13 item
types — CRS, UC, SYS, SYSARCH, MODULE, SRS, SWDD, RISK, RCM, SOUP, CR, DEF, REL —
each with its fields and lifecycle, plus the rules for which links are required
and the templates for the specifications. **Your project** adds files under
`DHF/config/` and `DHF/documents/specs/`. Where your project has one, it is used
instead of the default; where it has none, the default applies. That is why a new
project's `global.yaml` holds only its name, and why upgrading `medharness`
upgrades every default you have not overridden.

An override replaces the whole default it names; it never merges into it. Each
kind of default is overridden in its own place:

| To change | Do this | Example |
|---|---|---|
| A setting, such as which links are required | Write that key in `DHF/config/global.yaml`. Your value replaces the default value of that key, so copy the default value and edit it | `required_traceability: [...]` — your list is the whole list |
| The fields or lifecycle of an item type | Add `DHF/config/doc_types/srs.yaml` with `code: SRS`. It replaces the default SRS, so start from a copy of the default | give SRS a `hazard_ref` field |
| An item type of your own | Add a file in the same folder with a new `code` | `code: HWR` for hardware requirements |
| An item type you don't use | List its code in `omit_doc_types` in `global.yaml` | `omit_doc_types: [UC]` |
| A specification template | Add a file of the same name in `DHF/documents/specs/` | your own `requirements_specification.md.j2` |

Copy from the defaults in
[`dhfkit/templates/config/doc_types`](../dhfkit/templates/config/doc_types),
[`dhfkit/templates/config/global.yaml`](../dhfkit/templates/config/global.yaml)
and [`dhfkit/templates/specs`](../dhfkit/templates/specs).

The trade-off: an overridden item type stops following the package's changes to
that type, so override only what you change.

Projects scaffolded before 0.37 carry full copies of the config and templates.
They keep working: each copy overrides the default it duplicates. To follow the
defaults again, delete the copies you have not changed.

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
