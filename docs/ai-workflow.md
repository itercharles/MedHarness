# The AI-assisted CR workflow

How a change request becomes a design and then code: with the coding agent you already use, or unattended in CI. Every step is a separate command, so you can run it by hand or wire it into CI.

## With the coding agent you already use

`build plan --prompt` and `build code --prompt` print the stage (its steps and this CR's DHF context, exactly what the CI agent is given) for an agent that is already running, and start nothing. `init` writes the section below into `AGENTS.md`, which most coding agents read, and a `CLAUDE.md` that imports it. A project that predates it adds the section by hand:

```markdown

## Design History File

This repository keeps its Design History File in `DHF/`, checked by MedHarness.
A change to what the product does is not finished until its DHF is.

- **Start a change:** `medharness item create --type CR --data '{"title": "…", "description": "…"}'`,
  then `medharness item transition CR-NNN design`.
- **Design it:** run `medharness build plan --cr CR-NNN --prompt` and do what it says. Then show the user
  the design and wait for their approval before any code is written.
- **Build it:** run `medharness build code --cr CR-NNN --prompt` and do what it says.
- **Check it**, and fix what they report:
  - `medharness verify dhf`
  - `medharness verify impact --cr CR-NNN --code-path src/`
  - `medharness verify tests --cr CR-NNN --junit <results>`
- **Close it:** `medharness item transition CR-NNN completed`.

Go through `medharness item` for every DHF question and change, inside a CR or not:

- **Read** with `medharness item list --type <TYPE>` and `medharness item get <ID>`;
  `get` includes every ID the item links to.
- **Write** with `medharness item create|update|transition`, never by editing the
  files under `DHF/`: these check the schema before writing, allocate IDs, enforce
  the lifecycle, and change only the fields you pass.
- After any change, run `medharness verify dhf`.

Work locally. Do not push, open an issue or a pull request, or start a workflow unless you are asked to use CI.
```

Then ask your agent to "open a CR for the PDF export and update the DHF". It creates the CR, runs `build plan --cr CR-015 --prompt`, and does what it says.

## The stages

**`build plan --cr CR-001`** is the design. It triages the CR, works out what the change touches and what it leaves alone, writes the items that need to change, and records the analysis on the CR: `impact_analysis`, `implementation_notes`, `affected_items`, `reviewed_items`, `affected_risk_items`, and `triage_result` when it rejects. Before it finishes it checks that record, and fails the run, after one fix pass, when it is incomplete or names an item the DHF does not have. A CR that triage rejects stops there: no design, `outcome: rejected`, exit 1, the reason in `errors`.

**`build code --cr CR-001`** reads `implementation_notes` as its spec (it refuses a CR without them, naming `build plan`), writes the code, tags tests with `@links:<ITEM_ID>`, and runs a review loop. `artifacts.files_changed` lists the code changed on the branch; `MEDHARNESS_CODE_PATHS` (e.g. `src/,lib/`) narrows it.

Neither moves the CR's state. Move it with `medharness item transition`, by hand or from your workflow; `cr.yaml` says which moves exist and what each requires. The CR type must declare the six fields above: a project that drops one gets an error from `verify dhf`, and the stages refuse before any model runs.

The details of what `build plan` checks, and the warnings it gives (a created item that reads like an existing one, an item that grew by more than 40 lines, test points left unchanged), are in its prompt and in [interface.md](interface.md).

## Closing a CR

Before the merge, on the branch:

```bash
medharness --dhf DHF verify impact --cr CR-001 --code-path src/
medharness --dhf DHF verify tests --cr CR-001 --junit test-results
medharness --dhf DHF verify dhf --strict
```

The [`change-check` job](ci.md#setting-up-ci) of the CI recipe runs the first two for any branch named for its CR. Run `verify tests --cr` again on `main`, where the tests re-run against whatever else landed.

`verify tests --cr` judges only the items this CR touched, so the CR is not charged the DHF's other gaps. It requires the CR to carry what its type requires of the move to `completed`, whatever state it is in, so it can block the merge while the CR is still in `develop`. Those are, by default, `implementation_notes` (non-empty), `affected_items` and `affected_risk_items` (explicit lists, `[]` allowed); `item transition CR-001 completed` refuses on the same criteria. Every requirement in `affected_items` needs a `verification_method`, and one declaring `Test` needs passing JUnit evidence for each declared test point.

Approval is not their question. During development it is the review of the pull request, under your team's rules. At release the documents are signed and [`verify approval --release`](ci.md#signing-a-release) checks that.

## Wiring it into GitHub Actions

MedHarness does not interpret GitHub events; the workflow's own `if:` does. A sketch, with branches named `design/CR-NNN` and `develop/CR-NNN`:

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
    if: >-
      github.event_name == 'pull_request_review' && github.event.review.state == 'changes_requested'
      && contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.review.author_association)
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

- **Check out full history** (`fetch-depth: 0`) wherever a job runs `build plan|code`: they compare the branch with where it left its base, and a shallow clone cannot reach it. The base is the PR's target branch with `--pr`, otherwise `origin`'s HEAD, else `origin/main`; `--since-ref REF` overrides it.
- **Make `build code` pass your tests.** `--check CMD` (repeatable) names commands the code must pass. MedHarness runs them itself when the model is done and sends a failure back for a fix (two attempts); if one still fails the run exits non-zero and `--pr` pushes nothing. The job needs the project's toolchain installed. Without `--check`, nothing enforces the commands.
- **An issue is the agent's instructions.** `intake` turns an issue's title and body into the CR, so label only issues whose text you would hand to an agent with a shell. PRs opened with `github.token` start no workflows: give `gh pr create` another token if the PR's own checks should run.
- **`--pr` is CI; without it, local.** Without `--pr` the stages change files and commit nothing. With `--pr N` they revise when a reviewer has asked for changes on the PR's current commit, then commit and push to its branch; the job needs git's user configured and a token that can push. The agent never commits: if it does anyway, its commits are undone, the changes kept, and the answer carries an `agent_commits_undone` warning.
- `artifacts.items_changed` and `files_changed` are the whole branch against its base, not what one run added. `build plan` records `items_changed` as the CR's `affected_items`.

`build plan` and `build code` need the model's credentials in the job's environment: read [ai-security.md](ai-security.md) before giving them to a runner.
