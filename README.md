# MedHarness

**AI-assisted development with design control. For every change, an AI drafts
the design history — requirements, design, risk impact — and the code; ordinary
code checks that the two agree before anything merges.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

Regulated software needs a Design History File (DHF): every change traced from
requirement to design to test, with its risks assessed. MedHarness keeps the DHF
as plain YAML in your repository and makes it part of AI development: the agent
that writes the code also writes the DHF change, and deterministic checks, not a
model, decide whether the result traces and is verified.

## Quick start

```bash
pip install medharness
mkdir my-device && cd my-device
medharness init            # writes DHF/ with sample items, and AGENTS.md for your agent
```

Then ask your coding agent: *"open a CR for PDF export and implement it"*.
`AGENTS.md` tells it how: open a change request, draft the DHF change, write the
code, run the checks.

## AI development

Every change is a change request (CR) that goes through two stages, each ending
in a human review — of the pull request in CI, of the diff at your desk:

```mermaid
flowchart LR
    CR["CR opened"] --> PLAN["build plan<br/>AI analyses impact,<br/>drafts the DHF change"]
    PLAN --> REV{"Human review"}
    REV -.->|changes requested| PLAN
    REV -->|approved| CODE["build code<br/>AI writes code and tests"]
    CODE --> GATES["verify *<br/>ordinary code decides"]
    GATES -.->|fails| CODE
    GATES ==>|passes| MERGE["merge"]
    MERGE -.->|"tag v*"| REL["build release"]
```

`build plan` triages the CR, assesses its impact on risk, and writes the item
cascade it needs — requirements, design, test points — and an implementation
plan. `build code` implements that plan with tests linked to the requirements.
The same stages run two ways:

- **At your desk, with the agent you already use.** `build plan --cr CR-012
  --prompt` prints the stage's steps and the CR's DHF context, and starts
  nothing; your agent — Claude Code, Cursor, Codex, Copilot and the rest — does
  the work in your working tree, and you commit. The `AGENTS.md` that `init`
  writes tells any agent when to run it.
- **Fully automated in CI.** An issue starts it: the pipeline opens the CR,
  `build plan` drafts the design into a pull request, a reviewer approves or asks
  for changes — `build plan --pr N` revises from the review — and `build code`
  does the same for the code. The recipe, from issue label to merge, is in
  [adopting.md](docs/adopting.md#wiring-it-into-github-actions).

In CI, `build plan` and `build code` run the `claude` CLI by default
(`npm install -g @anthropic-ai/claude-code`), or any
`MEDHARNESS_{DESIGN,DESIGN_REVIEW,DEVELOP,CODE_REVIEW}_MODEL=provider:model`
(`anthropic`, `openai`, `deepseek`; `MEDHARNESS_{STAGE}_BASE_URL` for Azure,
Ollama or vLLM). They run an agent with a shell, so run them on an ephemeral CI
runner — read [ai-security.md](docs/ai-security.md) first.

## What a project looks like

```
my-device/
├── DHF/
│   ├── config/global.yaml       # the project name — and only what you change
│   └── items/                   # one YAML file per item, one directory per type
│       ├── 01_crs/CRS-001.yaml
│       ├── 03_srs/SRS-001.yaml
│       └── …                    # one directory per configured type
├── AGENTS.md                    # product context and DHF steps, for any coding agent
└── CLAUDE.md                    # @AGENTS.md, so Claude Code reads it too
```

Item types are configuration, not code. The package ships 13 default types —
CRS, UC, SYS, SYSARCH, MODULE, SRS, SWDD, RISK, RCM, SOUP, CR, DEF, REL — with
their fields, lifecycles, required links and specification templates. A project
uses those defaults as they are and keeps only what it overrides, so it picks up
improved defaults by upgrading `medharness`:

| To change | Do this |
|---|---|
| A setting, e.g. which links are required | Set its key in `global.yaml` — it replaces the default key |
| An item type's fields | Put `DHF/config/doc_types/<type>.yaml` — it replaces the default type of that code |
| A new item type | Add a file there with a new `code` |
| A type you don't use | `omit_doc_types: [UC]` in `global.yaml` |
| A specification template | Put a file of the same name in `DHF/documents/specs/` |

The defaults are in
[`dhfkit/templates/config`](dhfkit/templates/config) and
[`dhfkit/templates/specs`](dhfkit/templates/specs).

An item is a small YAML file. Links are written on the child and point up:

```yaml
id: SRS-012
title: Password must be at least 12 characters
derives_from: [SYS-004]
verification_method: [Test]
testing: |
  T1: an 11-character password is rejected
```

## Fitting it into what you already have

- **Tests.** Any runner that writes JUnit XML. Tag each test case with the
  requirement it verifies — the `medharness.links` property, or `@links:SRS-012`
  in the test name. In pytest: `@pytest.mark.dhf_links("SRS-012")`.
- **CI.** The smallest useful pipeline is two steps in a job that checks out
  the repository:

  ```yaml
  - run: pip install medharness==0.47.0
  - run: medharness verify dhf --strict
  ```

  The full recipe, including the release job, is in
  [adopting.md](docs/adopting.md#setting-up-ci).
- **Requirements kept elsewhere.** MedHarness reads the item files under
  `DHF/items/`. To check requirements that live in another tool, export them
  into that format — one YAML file per item — and run the same commands. The
  format is specified in [interface.md](docs/interface.md#the-item-format--integrating-another-system).

## Commands

One CLI. `--dhf PATH` goes before the command and defaults to `DHF`. Every
command writes JSON to stdout and readable lines to stderr; `--help` on any of
them lists its options. A failing check exits `1`.

### `item` — the records

| Command | What it does | Returns |
|---|---|---|
| `medharness item list --type SYS` | Lists items of a type | one JSON object per line |
| `medharness item get SRS-012` | One item | the item, with every ID it links to in `all_linked_uids` |
| `medharness item create --type SRS --data '{...}'` | Adds an item; its ID is allocated | the item |
| `medharness item update SRS-012 --data '{...}'` | Merges fields into an item; refuses what the schema would reject | the item |
| `medharness item transition CR-034 completed` | Moves an item through its lifecycle; without a state, lists where it can go | the item; without a state, `current_status` and `transitions` |

### `verify` — reads the DHF and the working tree, writes nothing

Ordinary code, never a model, decides whether a change is done; a team writing
its DHF by hand uses these the same way. Each answers `{gate, passed, summary,
errors, warnings}` — see [interface.md](docs/interface.md). Broken structure
always fails; what is only not yet written warns, unless you pass `--strict`.

| Command | Checks |
|---|---|
| `medharness verify dhf` | Schema, duplicate IDs, required and dangling links, cycles, coverage |
| `medharness verify tests --junit test-results` | Each requirement is verified by the method it declares |
| `medharness verify soup` | The SOUP register matches the manifests, and none of it is known-vulnerable |
| `medharness verify completion --cr CR-034` | A CR's record is complete and every item it changed is verified |
| `medharness verify changes --cr CR-034` | The branch diff against `origin/main`, uncommitted work included, matches the CR's `affected_items`, both ways |

### `build` — writes items, code or artifacts

| Command | What it does | Returns |
|---|---|---|
| `medharness build plan --cr CR-034` | AI drafts the CR's design items and impact analysis in the working tree, committing nothing; `--pr N` (CI) revises from that PR's reviews and pushes to it; `--prompt` prints the steps for an agent already running | `outcome`, `artifacts.items_changed`, `design_review`, `errors` |
| `medharness build code --cr CR-034` | AI writes the code and tests for the approved design; `--pr` and `--prompt` as for `plan` | `outcome`, `artifacts.files_changed`, `code_review`, `errors` |
| `medharness build soup` | Reconciles SOUP items with your dependency manifests, in the working tree | `to_create`, `to_update`, `orphans` |
| `medharness build release --version 1.0.0 --out-dir release --write` | Checks the DHF, CRs and open defects; writes the specifications, traceability, baseline, BOM, SBOM and evidence; and — only if every check passed — records the REL item. Without `--write` the DHF is not changed | `outcome`, `cr_ids`, `rel_uid`, `artifacts`, `errors`, `warnings` |

Approval has no command. Turn on GitHub branch protection for `main` with
*Require approvals* and *Dismiss stale pull request approvals when new commits
are pushed*: GitHub then refuses a merge unless the commit being merged was
approved.

### Setup

| Command | What it does | Returns |
|---|---|---|
| `medharness init` | Scaffolds `DHF/`, `AGENTS.md` and `CLAUDE.md` in the current directory, adding to either file if it exists; refuses if `DHF/` exists | `project_name`, `project_dir`, `created` |

## Example project

[ContourLab](https://github.com/itercharles/ContourLab) is an example project
used to exercise MedHarness end to end: its DHF, its CI, and changes made
through AI development.

## Documentation

| | |
|---|---|
| [adopting.md](docs/adopting.md) | starting fresh, the CI recipe, bringing an existing DHF, releases |
| [interface.md](docs/interface.md) | the gate result, exit codes, what may change |
| [ai-security.md](docs/ai-security.md) | what the AI stages can do, and running without them |
| [architecture.md](docs/architecture.md) | how the code is organised |
| [CHANGELOG.md](CHANGELOG.md) | version history |

## License

MIT. See [LICENSE](LICENSE).
