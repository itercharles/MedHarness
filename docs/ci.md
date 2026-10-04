# CI and releases

The CI recipe is the whole deployment; a release is cut from it. The AI stages in CI are in [the AI-assisted CR workflow](ai-workflow.md#wiring-it-into-github-actions).

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
