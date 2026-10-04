# The AI-assisted CR workflow

How a change request becomes a design and then code: with the coding agent you already use, or unattended in CI.

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

Runs triage, works out what the change touches and what it leaves alone (test files first, then a top-down drill), writes the items that need to change, and writes an implementation plan into `implementation_notes` on the CR item. Before it finishes it checks that the record is complete (below), so the fix pass can correct it. On completion the CR item carries:

| Field | Written by | Required at closure |
|-------|-----------|-------------------|
| `triage_result` | Step 2 (triage) | ✓ verdict must be `approved` |
| `impact_analysis` | Steps 1-5: assumptions, anchors with their evidence, every item examined and left unchanged, why each created item is not an update, and a verdict for each of nine dimensions | checked by `build plan`; not a closure gate |
| `affected_risk_items` | Step 6 (every risk and control relevant, changed or not) | ✓ explicit list (can be `[]`) |
| `implementation_notes` | Step 6 (impl plan) | ✓ non-empty |
| `affected_items` | Step 6; in CI, `build plan` and `build code` rewrite it from the branch | ✓ explicit list (can be `[]`) |
| `reviewed_items` | Step 6: items that depend on a changed one and were reviewed, needing no change | only as `verify changes` requires (below) |

`build plan` fails the run, after one fix pass, when the `impact_analysis` is missing a key or one of the nine dimensions; names an item the DHF does not have; leaves an anchor, a created item or a reviewed item without its evidence or reason; leaves a parent of a changed requirement neither changed nor reviewed; or leaves out a risk control that implements a changed item, or a risk it mitigates, from `affected_risk_items`. A created item that reads like an existing item of its type (similarity of 0.75 or more) is a warning, and so is an existing item that gained more than 40 lines (`large_edit`): a change to one behaviour is a line or two. A requirement whose `content` or `verification_criteria` changed while its `testing` points did not is a warning too (`test_points_unchanged`). A rejected CR is not checked.

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
        with: { fetch-depth: 0 }
      - run: pip install medharness
      - if: inputs.stage == 'plan'
        run: medharness build plan --cr "${{ inputs.cr }}"
      - if: inputs.stage == 'code'
        run: medharness build code --cr "${{ inputs.cr }}" --check "pnpm typecheck" --check "pnpm test"
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
        with: { ref: "${{ github.event.pull_request.head.ref }}", fetch-depth: 0 }
      - run: pip install medharness
      - run: |          # --pr: revise from the reviews, then commit and push to the PR
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          case "${BRANCH%%/*}" in
            design)  medharness build plan --cr "${BRANCH#*/}" --pr "$PR" ;;
            develop) medharness build code --cr "${BRANCH#*/}" --pr "$PR" --check "pnpm typecheck" --check "pnpm test" ;;
          esac
```

**Make `build code` pass your tests.** `--check CMD` (repeatable) names the commands the
code must pass. The model is told to run them and fix until they exit 0; when it is done,
MedHarness runs them itself and sends a failure back for a fix (two attempts). If one still
fails, the run exits non-zero, `checks` in the answer says which, and `--pr` pushes nothing.
A command that cannot run counts as failed (exit 127), so the job needs the project's
toolchain installed: without it the model can only guess, and the run fails instead of
shipping the guess. Without `--check`, the model finds the commands in `AGENTS.md` or
`CLAUDE.md` and nothing enforces them.

**Check out full history** (`fetch-depth: 0`) wherever a job runs `build plan|code`:
they compare the branch with where it left its base, and a shallow clone cannot reach that point
(the run stops with git's own reason). The base is found, not configured: with `--pr` the PR's
target branch, otherwise the branch `origin`'s HEAD points at, else `origin/main`. `--since-ref REF`
overrides it, for a change cut from a release branch; the answer's `inputs.since_ref` says which
was used. A `pull_request_review` run also uses the workflow file of the PR's head commit, so a branch cut before you fixed
the workflow keeps the old one until you update it with `main`.

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
its base, committed or not — the CR's whole change set across every run,
not what this run added. `build plan` records `items_changed` as the CR's
`affected_items`.

`build plan` and `build code` need the model's credentials in the job's
environment — see [ai-security.md](ai-security.md) before giving them to a
runner.
