# Interface

> **Stability:** Stable
> **Last reviewed:** 2026-09-30

What a script, a CI pipeline or a coding agent can rely on when it calls `medharness`: what each command does, what it prints, how it exits, and what may change. Tests check the facts stated here against the CLI.

MedHarness does not scaffold a CI workflow — a pipeline carries your runner labels, secrets and branch names, and a generated one would be wrong for most projects. This document is the other half of that decision: build the pipeline against it.

---

## The commands

One CLI, four groups. What each does is in the [command reference](#command-reference), generated from the CLI itself, so it lists every command and option and cannot drift.

- **`item`** reads or changes one DHF item at a time.
- **`verify`** judges the DHF, and a change against it. It writes nothing.
- **`build`** produces items, code or release artifacts.
- **`init`** scaffolds a project.

Rules every command shares:

- **The answer is on stdout, as JSON.** stderr carries readable lines for a person. **stderr is not a contract**: its wording changes freely, so never parse it — everything a caller needs is in the answer.
- **`--dhf PATH` goes before the command** (`medharness --dhf DHF verify dhf`) and defaults to `DHF`. No command takes its own.
- **Every command runs locally, as well as in CI.** Nothing commits or pushes, with one exception: `build plan` and `build code` take `--pr N` in CI, which revises from that pull request's reviews and then commits and pushes to its branch. Without `--pr` they change files in the working tree and stop. `build release` writes its artifacts to `--out-dir`, and records the REL item in the DHF only with `--write`.

### Exit codes

| Code | stdout | Meaning |
|------|--------|---------|
| `0` | JSON | The command succeeded, or the check passed |
| `1` | JSON | It ran and failed — a check found errors, or a build run ended in `tool_error` or `completed_with_errors` |
| `1` | *empty* | It never got to answer: a DHF that could not be read, an unknown item, an update the schema refuses |
| `2` | *empty* | Argument parsing error, e.g. an unknown flag |

A pipeline that only checks exit status is a valid consumer and needs to parse nothing.

**If you parse, check stdout is non-empty first.** Exit `1` means either a finding or a command that never answered, and only the first writes JSON. Treating an empty stdout as parseable is the one mistake this interface invites:

```python
lines = proc.stdout.splitlines()
if not lines:                     # the command never answered
    raise SystemExit(proc.stderr)
result = json.loads(lines[0])
```

---

## The checks (`verify`)

<!-- BEGIN GENERATED: gates — python scripts/generate_interface.py -->
| Gate | Checks | Options | Network | Blocking |
|---|---|---|---|---|
| `verify dhf` | Schema validity, required traceability, dangling links, and coverage between V-model layers. | `--strict` | no | `conditional` |
| `verify tests` | Requirement-to-test coverage from JUnit evidence, including declared test points. | `--junit`, `--strict` | no | `conditional` |
| `verify soup` | The SOUP register against the dependency manifests, and each item against the OSV vulnerability database, honouring documented per-CVE acceptances. | `--manifest`, `--strict`, `--offline-mode` | yes | `conditional` |
| `verify completion` | CR closure: mandatory CR fields, that the CR's affected_items exist, and verification evidence for each. | `--cr` (required), `--junit` | no | `always` |
| `verify changes` | That the branch, uncommitted work included, changes exactly the items its CR lists, and code when asked. | `--cr` (required), `--since-ref`, `--code-path` | no | `always` |
<!-- END GENERATED: gates -->

Every check answers from the machine it runs on, and none reads GitHub. Approval is not a check: GitHub's branch protection — required approvals, stale approvals dismissed on push — enforces it, on the server, where a pull request cannot edit the rule away.

### The result envelope

**stdout carries exactly one line of JSON**, with the same five keys for every check:

```json
{
  "gate": "verify tests",
  "passed": false,
  "summary": "1/3 requirement(s) covered by passing tests.",
  "errors": ["SYS: 0/1 requirements covered"],
  "warnings": ["SRS-001: no verification_method declared — pass --strict to block on this"]
}
```

<!-- BEGIN GENERATED: envelope — python scripts/generate_interface.py -->
| Key | Type | Meaning |
|---|---|---|
| `gate` | string | The command that produced this, e.g. `verify tests` |
| `passed` | boolean | Whether the check is satisfied. Always agrees with the exit code |
| `summary` | string | One line, never empty |
| `errors` | list of strings | What made the check fail. Empty when `passed` is true |
| `warnings` | list of strings | What the check noticed without failing |
<!-- END GENERATED: envelope -->

`errors` and `warnings` are **strings already phrased for a reader**, and they are the whole of what the check found: a caller that prints them produces a usable report without knowing which check it ran. There is no structured second copy — checks used to carry one under `details`, no caller read it, and its documented shape was wrong in three places by the time it was removed.

`summary` is where "what was checked" lives: `13 item(s) checked` distinguishes a real pass from a check that examined nothing.

A check that fails always populates `errors`. The test suite enforces that across every check; a `passed: false` with nothing to act on is a defect.

### What blocks a build

The `Blocking` column means:

| Value | Meaning |
|-------|---------|
| `always` | Any finding fails the check |
| `conditional` | Some findings always fail; others only under `--strict` (or, for `verify soup`, `--offline-mode`) |

`--strict` exists on `verify dhf`, `tests` and `soup`. For those three:

- `verify dhf` — schema errors, required-link failures, dangling links, links to a type the field does not accept (`satisfies` takes CRS only) and a `status` that is no state of the item's type always fail. Coverage gaps, and title or content that is still a placeholder (`placeholder_patterns` in `global.yaml`; the starter items' "Replace with your own", `TBD`), warn unless `--strict`. `build release` runs it strict, so the starter DHF cannot ship.
- `verify tests` — uncovered requirements and unverified tests always fail. A missing `verification_method` warns unless `--strict`.
- `verify soup` — known vulnerabilities always fail, and so does an unreachable osv.dev unless `--offline-mode warn`. Drift from the manifests warns unless `--strict`.

One distinction worth knowing before you wire anything: **broken references versus incomplete design.** `verify dhf` always fails on a link whose target does not exist — a typo or a deleted item. An item with no downstream child yet is normal mid-project and fails only under `--strict`. They need different fixes, so they are reported differently.

`verify changes` compares the working tree, uncommitted and untracked files included, against `--since-ref` (default `origin/main`), and needs that ref to be reachable — in CI, fetch it or check out with full history.

---

## Records (`item`)

`item` answers in the shape of the record, not the envelope.

| Command | stdout |
|---|---|
| `item list [--type T]` | one JSON object per line, one per item; the count goes to stderr |
| `item get ID` | the item |
| `item create --type T --data JSON` | the item, with its allocated ID |
| `item update ID --data JSON` | the item after the merge |
| `item transition ID STATE` | the item in its new state |
| `item transition ID` | `item_id`, `current_status` and `transitions` — where it can go, and what blocks each move |

An item is its file's fields plus `type` (the doc type's code), `file_path`, and `all_linked_uids` — every ID it links to, so a caller need not know which fields are links.

`create` and `update` validate against the doc type's schema **before writing**: an unknown field or a missing required field exits `1` with nothing on stdout and the reason on stderr, and no file is written. `update` changes only the fields it is given, and rewrites only the fields whose value changed, so a review shows the field that changed and nothing else.

---

## Build

`build` commands are not checks and do not answer with the envelope; each answers with its own report, whose fields are listed [below](#reports).

- **`build plan` and `build code`** exit `1` when the `outcome` is `completed_with_errors` or `tool_error`. Their execution boundary is in [ai-security.md](ai-security.md).
- **`--prompt`** on either prints Markdown, not JSON: the stage's steps and the CR's DHF context, for an agent that is already running. It starts no model and changes nothing. It is the only output that is not JSON.
- **`build soup`** always writes the SOUP items in the working tree. Exit `1` on `completed_with_errors`.
- **`build release`** exits `1` when any check failed; a failing release still writes its evidence to `--out-dir`, so you can read why, but records no REL item.

## Reports

The fields of what each command above answers with, generated from the models in `medharness/results.py`. Tests validate real output against them, so a key that is not listed here, or listed and missing, fails the build.

<!-- BEGIN GENERATED: shapes — python scripts/generate_interface.py -->
#### `build plan`

| Field | Type | Meaning |
|---|---|---|
| `cr_id` | string | The CR the run was for |
| `outcome` | `ok` · `corrected` · `completed_with_errors` · `tool_error` | `ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; `tool_error` when a critical step failed. The last two exit 1 |
| `summary` | string | The outcome in a sentence |
| `timing` | `Timing` | When it started and how long it took |
| `inputs` | `Inputs` | What the run was given |
| `progress` | `Progress` | How far it got |
| `steps` | list of `Step` | Every step, in order |
| `diagnostics` | object | Models used, the session id, fix and review counts, PR feedback; the keys vary by stage |
| `warnings` | list of `RunWarning` | What the run noticed without failing |
| `errors` | list of `RunError` | Empty unless the run ended with errors |
| `pr_comments` | list of strings or null | With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors |
| `stage` | `generate_dhf` | Always `generate_dhf` for `build plan` |
| `artifacts` | `PlanArtifacts` | What the run changed |
| `design_review` | `Review` or null | The design review rounds, when one ran |

`Timing`:

| Field | Type | Meaning |
|---|---|---|
| `started_at` | string | When the run started, ISO 8601 UTC |
| `elapsed_ms` | integer | How long it took |

`Inputs`:

| Field | Type | Meaning |
|---|---|---|
| `dhf_path` | string | The `--dhf` the run used |
| `repo_root` | string | The repository the DHF is in |
| `pr_number` | integer or null | The `--pr` it was given, or null |
| `revision_mode` | boolean | True when it revised from a reviewer's changes instead of generating |
| `since_ref` | string | What the branch is compared against |

`Progress`:

| Field | Type | Meaning |
|---|---|---|
| `current_step` | string or null | The step running when the report was written, or null |
| `completed_steps` | integer | Steps finished |
| `total_steps` | integer | Steps in the run |

`Step`:

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The step, e.g. `run_initial_generation`, `validate_initial`, `run_review` |
| `started_at` | string | When it started, ISO 8601 UTC |
| `elapsed_ms` | integer | How long it took |
| `outcome` | string | `ok`, `warning` or `error` |
| `details` | object | Facts about the step; the keys vary by step |

`RunWarning`:

| Field | Type | Meaning |
|---|---|---|
| `code` | string | A stable identifier, e.g. `agent_commits_undone` |
| `message` | string | The warning, phrased for a reader |
| `details` | object or null | Extra facts, when the warning has any |

`RunError`:

| Field | Type | Meaning |
|---|---|---|
| `field` | string | What was wrong, as a dotted path such as `traceability.dangling.satisfies` |
| `issue` | string | The problem, phrased for a reader |
| `fix` | string | What to do about it |
| `code` | string | A stable identifier derived from `field` |

`PlanArtifacts`:

| Field | Type | Meaning |
|---|---|---|
| `items_changed` | `ChangeSet` or null | The DHF items changed on the branch, the CR's whole change set; null when the diff could not be read |
| `design_impact` | `DesignImpact` or null | The CR's `affected_items` write-back |

`Review`:

| Field | Type | Meaning |
|---|---|---|
| `cycles` | list of `ReviewCycle` | One entry per review round |
| `narrative` | list of strings | The rounds as sentences, for a log |

`ChangeSet`:

| Field | Type | Meaning |
|---|---|---|
| `created` | list of strings | Created since `since_ref`, committed or not |
| `updated` | list of strings | Modified since `since_ref` |
| `deleted` | list of strings | Deleted since `since_ref` |

`DesignImpact`:

| Field | Type | Meaning |
|---|---|---|
| `recorded` | boolean | Whether the CR's `affected_items` was written |
| `reason` | string | Why or why not, e.g. `updated` |
| `affected_items` | list of strings or null | The items recorded, when they were |

`ReviewCycle`:

| Field | Type | Meaning |
|---|---|---|
| `cycle` | integer | 1 for the first review, up to 3 |
| `verdict` | `approved` · `needs_revision` · `unknown` | What the reviewer concluded |
| `issues` | list of strings | What it asked to change |

#### `build code`

| Field | Type | Meaning |
|---|---|---|
| `cr_id` | string | The CR the run was for |
| `outcome` | `ok` · `corrected` · `completed_with_errors` · `tool_error` | `ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; `tool_error` when a critical step failed. The last two exit 1 |
| `summary` | string | The outcome in a sentence |
| `timing` | `Timing` | When it started and how long it took |
| `inputs` | `Inputs` | What the run was given |
| `progress` | `Progress` | How far it got |
| `steps` | list of `Step` | Every step, in order |
| `diagnostics` | object | Models used, the session id, fix and review counts, PR feedback; the keys vary by stage |
| `warnings` | list of `RunWarning` | What the run noticed without failing |
| `errors` | list of `RunError` | Empty unless the run ended with errors |
| `pr_comments` | list of strings or null | With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors |
| `stage` | `develop` | Always `develop` for `build code` |
| `artifacts` | `CodeArtifacts` | What the run changed |
| `code_review` | `Review` or null | The code review rounds, when one ran |

`CodeArtifacts`:

| Field | Type | Meaning |
|---|---|---|
| `files_changed` | `ChangeSet` or null | The code changed on the branch; null when the diff could not be read |

`Timing`, `Inputs`, `Progress`, `Step`, `RunWarning`, `RunError`, `Review`, `ChangeSet`, `ReviewCycle` are as listed above.

#### `build soup`

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `completed` · `completed_with_errors` | `completed_with_errors` exits 1 |
| `manifests_parsed` | list of strings | The manifests it read |
| `packages_found` | integer | Packages across them |
| `to_create` | list of strings | Packages with no SOUP item |
| `to_update` | list of `SoupDrift` | SOUP items whose version has drifted |
| `orphans` | list of `SoupOrphan` | SOUP items no manifest resolves |
| `matched_count` | integer | Packages that already have a matching SOUP item |
| `items_created` | list of strings | SOUP items it wrote, in the working tree |
| `items_updated` | list of strings | SOUP items it changed, in the working tree |
| `errors` | list of strings | Manifests or commands that could not be read |

`SoupDrift`:

| Field | Type | Meaning |
|---|---|---|
| `uid` | string | The SOUP item |
| `name` | string | The package |
| `old_version` | string | What the register says |
| `new_version` | string | What the manifest says |

`SoupOrphan`:

| Field | Type | Meaning |
|---|---|---|
| `uid` | string | The SOUP item no manifest resolves |
| `name` | string | The package |

#### `build release`

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `completed` · `completed_with_errors` | `completed_with_errors` exits 1; a failing release still writes its evidence |
| `version` | string | The version released |
| `cr_ids` | list of strings | The completed CRs it includes |
| `rel_uid` | string or null | The REL item recorded; null without `--write` or when a check failed |
| `soup_count` | integer | SOUP items in the BOM |
| `artifacts` | list of strings | Files written under `--out-dir`, relative to it |
| `errors` | list of strings | What blocked the release |
| `warnings` | list of strings | What it noticed without blocking, such as a component with no purl |

#### `init`

| Field | Type | Meaning |
|---|---|---|
| `project_name` | string | The name written into `global.yaml` |
| `project_dir` | string | Where the project was scaffolded |
| `created` | list of strings | Files created, relative to `project_dir` |
<!-- END GENERATED: shapes -->

---

## The item format — integrating another system

By default every command reads YAML files under `DHF/items/`, and that format is the simplest integration surface: a team whose requirements live in another tool exports them into it and runs the same commands. To read items from the tool directly instead, an installed adapter is chosen with `store:` in `global.yaml` — see [architecture.md](architecture.md#item-adapters). `verify changes`, `build plan` and `build code` need the files in Git and refuse another store.

```yaml
# DHF/items/03_srs/SRS-012.yaml
id: SRS-012                       # required; the prefix decides the type
title: Password must be at least 12 characters
derives_from: [SYS-004]           # a link: a list of IDs, written on the child
verification_method: [Test]
```

| Rule | |
|---|---|
| One file per item | Named anything ending `.yaml`; the directory under `items/` does not matter, so an export can use its own |
| `id` | Required. Its prefix (`SRS-`) picks the doc type |
| Fields | Only those the doc type declares. An undeclared field fails `medharness verify dhf`, naming it — declare it by overriding the doc type first |
| Links | Fields of format `relationship` or `item_multiselect`: a list of IDs pointing up the V-model, each of a type the field's `target_types` accepts. Which are required is `required_traceability` in `global.yaml` |
| Types | The 13 defaults, plus any `DHF/config/doc_types/<type>.yaml` of your own, which replaces the default of that code — see [adopting.md](adopting.md#changing-the-defaults) |

Check an export with `medharness verify dhf`: it validates each file against its type, then the links and coverage of the design they describe.

The format is covered by `CONTRACT_VERSION`: renaming or removing a field the defaults declare is a breaking change.

---

## Stability

What a caller may rely on:

- **The five envelope keys** are stable. New keys may be added at the top level; existing ones will not be removed or change type without a major version.
- **Exit code meanings** are stable.
- **The commands and their options.** A new one is announced in the changelog; a renamed or removed one is a breaking change.
- **The item file format**, as above.
- **stderr, and the exact wording of `errors`, `warnings` and `summary`,** are not stable — they are written for a person.

Changes to any of the stable items are called out as breaking in the changelog.

---

## Consuming it

### From a pipeline

The simplest correct consumer checks exit status and lets stderr reach the log:

```yaml
- name: DHF checks
  run: |
    medharness --dhf DHF verify dhf --strict
    medharness --dhf DHF verify tests --junit test-results
    medharness --dhf DHF verify soup
```

To turn findings into annotations, read the envelope:

```bash
medharness --dhf DHF verify dhf --strict > result.json || true
jq -r '.errors[] | "::error::\(.)"' result.json
jq -r '.warnings[] | "::warning::\(.)"' result.json
exit "$(jq -r 'if .passed then 0 else 1 end' result.json)"
```

### From an agent or a script

Because every check answers alike, one loop covers all of them:

```python
import json, subprocess

CHECKS = [
    ["verify", "dhf", "--strict"],
    ["verify", "tests", "--junit", "test-results"],
    ["verify", "soup"],
]

for check in CHECKS:
    proc = subprocess.run(["medharness", *check], capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    if not lines:                 # the check never ran
        raise SystemExit(f"{' '.join(check)}: {proc.stderr.strip()}")
    result = json.loads(lines[0])
    if not result["passed"]:
        report(result["gate"], result["errors"])
```

An agent that only needs to read or change the DHF uses `item`, never the files: see [the section `init` writes into `AGENTS.md`](adopting.md#with-the-coding-agent-you-already-use).

---

## Command reference

Generated from the CLI by `python scripts/generate_interface.py`; a test fails when it is out of date. `--help` on any command prints its full description.

<!-- BEGIN GENERATED: reference — python scripts/generate_interface.py -->
| Command | What it does |
|---|---|
| `item get` | Get a single DHF item by ID. Outputs JSON. |
| `item list` | List DHF items. Outputs one JSON object per line. |
| `item create` | Create a new DHF item. Outputs the created item as JSON. |
| `item update` | Update fields of an existing DHF item. |
| `item transition` | Move an item to TO_STATE, or list where it can go when TO_STATE is omitted. |
| `verify dhf` | Check the DHF holds together: schema, links, cycles, coverage. |
| `verify tests` | Check each requirement is verified by the method it declares. |
| `verify completion` | Check a CR's record is complete and the items it changed are verified. |
| `verify changes` | Check the branch changed the items the CR said it would. |
| `verify soup` | Check the SOUP register matches what ships, and is not known-vulnerable. |
| `build plan` | Draft the DHF item cascade and impact analysis for a CR, with a model. |
| `build code` | Write the code and tests for a CR's approved design, with a model. |
| `build release` | Build everything one release needs (IEC 62304 §9). |
| `build soup` | Reconcile SOUP items from the project's dependency manifests. |
| `init` | Scaffold a DHF, and the AGENTS.md coding agents read, in the current directory. |

#### `medharness item get ITEM_ID`

Get a single DHF item by ID. Outputs JSON.

#### `medharness item list`

List DHF items. Outputs one JSON object per line.

| Option | |
|---|---|
| `--type CODE` | Filter by doc type code (e.g. SYS). |

#### `medharness item create`

Create a new DHF item. Outputs the created item as JSON.

| Option | |
|---|---|
| `--type CODE` | Doc type code (e.g. SYS, SRS). [required] |
| `--data JSON` | Item fields as JSON object. [required] |

#### `medharness item update ITEM_ID`

Update fields of an existing DHF item.

| Option | |
|---|---|
| `--data JSON` | Fields to update as JSON (merged into existing). [required] |

#### `medharness item transition ITEM_ID [TO_STATE]`

Move an item to TO_STATE, or list where it can go when TO_STATE is omitted.

#### `medharness verify dhf`

Check the DHF holds together: schema, links, cycles, coverage.

| Option | |
|---|---|
| `--strict` | Exit non-zero when items lack downstream coverage. Without it, coverage gaps are reported as WARN only. |

#### `medharness verify tests`

Check each requirement is verified by the method it declares.

| Option | |
|---|---|
| `--junit PATH` | JUnit XML results: a file, or a directory searched for *.xml (repeatable). |
| `--strict` | Make a requirement with no declared verification_method fail. Warns by default, so a project adding the field is not blocked. |

#### `medharness verify completion`

Check a CR's record is complete and the items it changed are verified.

| Option | |
|---|---|
| `--cr CR_ID` | The CR to close. [required] |
| `--junit PATH` | JUnit XML results for the items this CR touched: a file, or a directory searched for *.xml (repeatable). |

#### `medharness verify changes`

Check the branch changed the items the CR said it would.

| Option | |
|---|---|
| `--cr CR_ID` | The CR whose affected_items the branch must change. [required] |
| `--since-ref REF` | What the branch is compared against. |
| `--code-path PATH` | Opt into code-change enforcement: path(s) under which at least one file must be modified. Omitting this option skips the code-change check entirely. |

#### `medharness verify soup`

Check the SOUP register matches what ships, and is not known-vulnerable.

| Option | |
|---|---|
| `--manifest PATH` | Dependency manifest to compare the register against (repeatable). Auto-discovers when omitted. |
| `--strict` | Make an undocumented or misversioned component fail the gate. Warns by default, so a project backfilling its register is not blocked. |
| `--offline-mode [fail|warn]` | Behaviour when osv.dev is unreachable. 'warn' keeps the gate passing for air-gapped or proxy-restricted pipelines. |

#### `medharness build plan`

Draft the DHF item cascade and impact analysis for a CR, with a model.

| Option | |
|---|---|
| `--cr CR_ID` | The CR to design: its item cascade and impact analysis. [required] |
| `--pr N` | The PR this run belongs to, in CI: revise if a reviewer asked for changes, then commit and push the result to its branch. Without it, local files change and nothing is committed. |
| `--prompt` | Print the stage's instructions, with this CR's DHF context, for an agent that is already running, instead of starting a model. |

#### `medharness build code`

Write the code and tests for a CR's approved design, with a model.

| Option | |
|---|---|
| `--cr CR_ID` | The CR whose approved design to implement. [required] |
| `--pr N` | The PR this run belongs to, in CI: revise if a reviewer asked for changes, then commit and push the result to its branch. Without it, local files change and nothing is committed. |
| `--prompt` | Print the stage's instructions, with this CR's DHF context, for an agent that is already running, instead of starting a model. |

#### `medharness build release`

Build everything one release needs (IEC 62304 §9).

| Option | |
|---|---|
| `--version VERSION` | The version being released, e.g. 1.2.0. [required] |
| `--out-dir DIRECTORY` | Where to write the baseline, BOM, SBOM and evidence bundle. [required] |
| `--write` | Record a REL item in the DHF. Happens only when every check passed; without it the DHF is not changed. |
| `--cr CR_ID` | A CR to include (repeatable). Default: every completed CR not yet in a release. |
| `--manifest PATH` | Dependency manifest whose packages the BOM lists beside the SOUP register (repeatable). |
| `--junit PATH` | JUnit XML to include as test evidence: a file, or a directory searched for *.xml (repeatable). |
| `--doc-format [html|pdf]` | Format of the bundled specifications. PDF needs medharness[docs] plus cairo/pango. [default: html] |

#### `medharness build soup`

Reconcile SOUP items from the project's dependency manifests.

| Option | |
|---|---|
| `--manifest PATH` | Manifest to read (repeatable). Auto-discovers when omitted. |
| `--from-command CMD` | External tool emitting NDJSON components (repeatable). |

#### `medharness init`

Scaffold a DHF, and the AGENTS.md coding agents read, in the current directory.
<!-- END GENERATED: reference -->
