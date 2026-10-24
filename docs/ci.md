# CI and releases

The CI recipe is the whole deployment; a release is cut from it. The AI stages in CI are in [the AI-assisted CR workflow](ai-workflow.md#wiring-it-into-github-actions).

## Setting up CI

`init` does not write a CI workflow, because the pipeline references your branch names, runner labels and secrets. You own it.

Copy the recipe below into `.github/workflows/dhf.yml`, replace `{{medharness_version}}` with the version you pin, and `{{test_command}}` with the command that runs your tests and writes JUnit XML into `test-results/` (for pytest, `pytest --junit-xml=test-results/junit.xml`). It is the whole deployment — two jobs, no server, no database, no account:

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

      # Every requirement must be verified by this run's JUnit: the release is cut
      # from the tests of the commit it ships, not from a result produced elsewhere.
      - name: Run the tests
        run: "{{test_command}}"

      - name: Build the release
        env:
          VERSION: ${{ steps.ver.outputs.version }}
        run: |
          medharness --dhf DHF build release \
            --version "$VERSION" \
            --out-dir artifacts \
            --junit test-results \
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

## Cutting a release (`build release`)

```bash
medharness --dhf DHF build release --version 1.2.0 --out-dir release --junit test-results
```

`--junit` is required: every requirement must be verified by it, as `verify tests --strict` judges it, whether or not an included CR touched it. One command builds everything a release needs, into one directory: the release baseline, the software BOM, a CycloneDX SBOM, the specifications, a traceability report for each matrix in `traceability_matrices`, test evidence, and `evidence-manifest.json` hashing every file.

Before writing anything to the DHF it checks that:

- the DHF passes `verify dhf` — with coverage gaps failing, since a release is not the place for advisory findings;
- every included CR is `completed` (by default, every completed CR not yet in a release; `--cr` to choose) **and still passes `verify completion`** — `completed` is a status anyone can write, so the gate is run again, with the `--junit` evidence;
- every open defect carries a `release_rationale` (IEC 62304 §9.7).

Add `--write` to record the REL item. It is recorded **only when every check passed** — a failing release still writes its evidence, so you can read why, but leaves the DHF unchanged. The [CI recipe](#setting-up-ci) runs it on `v*` tags and brings the REL item back to `main` through a pull request.

## Signing a release

When the project keeps `DHF/config/approvers.yaml` (each person with their roles and public keys), a release is signed before it is issued. `approval_roles` and `release_role` in `global.yaml` say which role owns which specification. Without that file none of this applies. The reasoning is in [ADR-004](adr/ADR-004-signed-approvals.md).

```bash
medharness --dhf DHF build release --version 1.2.0 --out-dir release --junit test-results --write
medharness --dhf DHF item approve --release 1.2.0 --key ~/.ssh/id_ed25519_sk
medharness --dhf DHF verify approval --release 1.2.0
medharness --dhf DHF build approvals --release 1.2.0 --out-dir release
```

1. **Run the release.** `--write` also writes `DHF/releases/1.2.0/manifest.yaml`, the item hashes each specification consists of, and `changes.md`, what changed in each since the previous release. Commit both on the release branch.
2. **Each signer approves.** `item approve --release` shows the changes to the documents the signer's roles own, asks for confirmation, and writes one signed record under `DHF/approvals/release-1.2.0/`. Commit it; the record proves itself, so who commits it does not matter.
3. **Check it.** `verify approval --release` passes when every document of the manifest has a valid signature from its role over its current content, and the release has the quality lead's. An item edited after the manifest was written fails it: run `build release --write` again and sign the affected documents again.
4. **Render the sheet.** `build approvals` runs that same check and, only if it passes, writes `approval-sheet.html` (or `.pdf` with `--doc-format pdf`): for each document its hashes and every signature over it, with the signer, roles, time, statement, key fingerprint and record ID, and a warning on a signature made without proven presence. The sheet presents the records; they stay the evidence. Every specification a release renders says, when an approvers list exists, to see this sheet.
