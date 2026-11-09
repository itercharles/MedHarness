# Interface

> **Stability:** Stable
> **Last reviewed:** 2026-11-07

What a script, a CI pipeline or a coding agent can rely on when it calls `medharness`: what it prints, how it exits, and what may change. Tests check the facts stated here against the CLI. Options are not repeated: `--help` on any command lists them.

MedHarness does not scaffold a CI workflow — a pipeline carries your runner labels, secrets and branch names, and a generated one would be wrong for most projects. Build yours against this page; [ci.md](ci.md) has a recipe to start from.

---

## Every command

- **The answer is on stdout, as JSON.** stderr carries readable lines for a person. **stderr is not a contract**: its wording changes freely, so never parse it.
- **`--dhf PATH` goes before the command** (`medharness --dhf DHF verify dhf`) and defaults to `DHF`.
- **Commands run locally, as well as in CI.** Nothing commits or pushes, with one exception: `build plan` and `build code` take `--pr N` in CI, which revises from that pull request's reviews and then commits and pushes to its branch. `build release` writes its artifacts to `--out-dir` and records the REL item in the DHF only with `--write`.
- **`--prompt`** on `build plan` and `build code` prints Markdown, not JSON: the stage's steps and the CR's DHF context, for an agent that is already running. It starts no model and changes nothing.

### Exit codes

| Code | stdout | Meaning |
|------|--------|---------|
| `0` | JSON | The command succeeded, or the check passed |
| `1` | JSON | It ran and failed — a check found errors, or a build run ended in `tool_error`, `rejected` or `completed_with_errors` |
| `1` | *empty* | It never got to answer: a DHF that could not be read, an unknown item, an update the schema refuses |
| `2` | *empty* | Argument parsing error, e.g. an unknown flag |

A pipeline that only checks exit status needs to parse nothing. If you parse, check stdout is non-empty first: exit `1` means either a finding or a command that never answered, and only the first writes JSON.

---

## Commands

`verify` commands answer with the [envelope](#the-checks-verify), `item` with the record, and the rest with the [report](#build) below.

<!-- BEGIN GENERATED: reference — python scripts/generate_interface.py -->
| Command | What it does |
|---|---|
| `item get` | Get a single DHF item by ID. Outputs JSON. |
| `item list` | List DHF items in ID order. Outputs one JSON object per line. |
| `item create` | Create a new DHF item. Outputs the created item as JSON. |
| `item update` | Update fields of an existing DHF item. |
| `item transition` | Move an item to TO_STATE, or list where it can go when TO_STATE is omitted. |
| `item approve` | Sign a release's documents, or the approvers list. |
| `build plan` | Draft the DHF item cascade and impact analysis for a CR, with a model. |
| `build code` | Write the code and tests for a CR's approved design, with a model. |
| `build release` | Build everything one release needs (IEC 62304 §9). |
| `build approvals` | Write the approval sheet of a signed release: who approved which documents. |
| `build validation` | Validate this installation: run the shipped validation set and write a report to file. |
| `build soup` | Reconcile SOUP items from the project's dependency manifests. |
| `init` | Scaffold a DHF, and the AGENTS.md coding agents read, in the current directory. |
<!-- END GENERATED: reference -->

---

## The checks (`verify`)

<!-- BEGIN GENERATED: gates — python scripts/generate_interface.py -->
| Gate | Checks | Network | Blocking |
|---|---|---|---|
| `verify dhf` | Schema validity, required traceability, dangling links, coverage between V-model layers, and that a completed CR has what its type requires of one. | no | `conditional` |
| `verify tests` | Requirement-to-test coverage from JUnit evidence, including declared test points; with --cr, only for the items one CR changed. | no | `conditional` |
| `verify soup` | The SOUP register against the dependency manifests, and each item against the OSV vulnerability database, honouring documented per-CVE acceptances. | yes | `conditional` |
| `verify impact` | That the CR's record of its impact (impact_analysis, reviewed_items, affected_risk_items) is complete, evidenced and settles every item the branch's changes reach, and that the branch changes exactly the items the CR lists. | no | `always` |
| `verify approval` | That every approval is signed by an approver holding its roles, that approvals are only added, and that a change to the approvers list is approved from the list as it was. With --release: that each document of the release manifest and the release itself carry a current signature from their role. | no | `always` |
<!-- END GENERATED: gates -->

Every check answers from the machine it runs on, and none reads GitHub. During development, approval is the review of the pull request under the team's own rules. At release, approval is a signature: `item approve --release` signs the documents a role owns, `verify approval --release` checks the signatures from the files in the repository, and `build approvals` renders who signed what ([ADR-004](adr/ADR-004-signed-approvals.md)).

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

`errors` and `warnings` are strings already phrased for a reader, and they are the whole of what the check found: a caller that prints them produces a usable report without knowing which check it ran. `summary` is where "what was checked" lives: `13 item(s) checked` distinguishes a real pass from a check that examined nothing. A check that fails always populates `errors`.

### What blocks a build

| Value | Meaning |
|-------|---------|
| `always` | Any finding fails the check |
| `conditional` | Some findings always fail; others only under `--strict` (or, for `verify soup`, `--offline-mode`) |

- `verify dhf` — schema errors, required-link failures, dangling links, links to a type the field does not accept and a `status` that is no state of the item's type always fail. Coverage gaps, and title or content that is still a placeholder (`placeholder_patterns` in `global.yaml`), warn unless `--strict`. `build release` runs it strict, so the starter DHF cannot ship.
- `verify tests` — uncovered requirements and unverified tests always fail. A missing `verification_method`, and a test that claims a test point its requirement does not declare, warn unless `--strict`.
- `verify soup` — known vulnerabilities always fail, and so does an unreachable osv.dev unless `--offline-mode warn`. Drift from the manifests warns unless `--strict`.

A link whose target does not exist (a typo, a deleted item) always fails; an item with no downstream child yet is normal mid-project and fails only under `--strict`.

`verify impact` compares the working tree, uncommitted and untracked files included, against `--since-ref` (default `origin/main`), which must be reachable: in CI, fetch it or check out with full history. It checks that the branch changes exactly the items its CR lists in `affected_items` (and, with `--code-path`, that some file under it changed), and the CR's record of its impact: `impact_analysis` complete and evidenced, naming only items the DHF has, and every item the branch's changes reach either changed or listed in `reviewed_items`; what it reads is in [configuration.md](configuration.md#what-verify-impact-reads). A CR marked rejected (`triage_result.verdict: rejected`) is exempt only while its branch changes nothing but the CR.

---

## Records (`item`)

`item` answers in the shape of the record, not the envelope.

| Command | stdout |
|---|---|
| `item list` | one JSON object per line, in ID order (by prefix, then number: `SRS-999` before `SRS-1000`); the count goes to stderr |
| `item get ID` | the item |
| `item create`, `item update ID` | the item after the write, with its ID |
| `item transition ID STATE` | the item in its new state |
| `item transition ID` | `item_id`, `current_status` and `transitions` — where it can go, and what blocks each move |
| `item approve` | the approval record written, with its path |

An item is its file's fields plus `type` (the item type's code), `file_path`, and `all_linked_uids` — every ID it links to, so a caller need not know which fields are links.

`create` and `update` validate against the item type's schema **before writing**: an unknown field or a missing required field exits `1` with nothing on stdout and the reason on stderr, and no file is written. `update` changes only the fields it is given, and rewrites only those whose value changed, so a review shows the field that changed and nothing else.

---

## Build

`build` commands do not answer with the envelope; each answers with its own report.

- **`build plan` and `build code`** exit `1` when the `outcome` is `completed_with_errors`, `tool_error` or `rejected`. Their execution boundary is in [ai-security.md](ai-security.md).
- **`build soup`** always writes the SOUP items in the working tree. Exit `1` when `errors` is not empty.
- **`build release`** exits `1` when any check failed; a failing release still writes its evidence to `--out-dir`, so you can read why, but records no REL item.
- **`build approvals`** runs `verify approval --release` first and exits `1` when it fails, writing no sheet.
- **`build validation`** runs the validation set that ships in the package against scratch projects; it reads no DHF, and `--dhf` is ignored. It answers with the verdict and the path of the report it wrote, which holds the rest. It exits `1` unless `result` is `passed`. See [adopting.md](adopting.md#validating-your-installation).

<!-- BEGIN GENERATED: shapes — python scripts/generate_interface.py -->
#### `build plan`

| Field | Type | Meaning |
|---|---|---|
| `cr_id` | string | The CR the run was for |
| `outcome` | `ok` · `corrected` · `completed_with_errors` · `tool_error` · `rejected` | `ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; `tool_error` when a critical step failed; `rejected` when triage turned the CR down (the reason is in `errors`, no design was generated). The last three exit 1 |
| `summary` | string | The outcome in a sentence |
| `steps` | list of `Step` | Every step, in order |
| `warnings` | list of `RunWarning` | What the run noticed without failing |
| `errors` | list of `RunError` | Empty unless the run ended with errors |
| `pr_comments` | list of strings or null | With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors |
| `stage` | `generate_dhf` | Always `generate_dhf` for `build plan` |
| `artifacts` | `PlanArtifacts` | What the run changed |
| `design_review` | `Review` or null | The design review rounds, when one ran |

`Step`:

| Field | Type | Meaning |
|---|---|---|
| `name` | string | The step, e.g. `run_initial_generation`, `validate_initial`, `run_review` |
| `started_at` | string | When it started, ISO 8601 UTC |
| `elapsed_ms` | integer | How long it took |
| `outcome` | string | `ok`, `warning` or `failed` |

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
| `outcome` | `ok` · `corrected` · `completed_with_errors` · `tool_error` · `rejected` | `ok`; `corrected` after a fix pass; `completed_with_errors` when errors remain; `tool_error` when a critical step failed; `rejected` when triage turned the CR down (the reason is in `errors`, no design was generated). The last three exit 1 |
| `summary` | string | The outcome in a sentence |
| `steps` | list of `Step` | Every step, in order |
| `warnings` | list of `RunWarning` | What the run noticed without failing |
| `errors` | list of `RunError` | Empty unless the run ended with errors |
| `pr_comments` | list of strings or null | With `--pr`: the URLs of the comments it posted on the PR to report warnings or errors |
| `stage` | `develop` | Always `develop` for `build code` |
| `artifacts` | `CodeArtifacts` | What the run changed |
| `code_review` | `Review` or null | The code review rounds, when one ran |
| `checks` | list of `CheckResult` or null | Each `--check` as the harness last ran it; absent without `--check` |

`CodeArtifacts`:

| Field | Type | Meaning |
|---|---|---|
| `files_changed` | `ChangeSet` or null | The code changed on the branch; null when the diff could not be read |

`CheckResult`:

| Field | Type | Meaning |
|---|---|---|
| `command` | string | The `--check` command, as given |
| `exit_code` | integer | What it exited with in the last run; 124 when it timed out |
| `passed` | boolean | Whether it exited 0 |

`Step`, `RunWarning`, `RunError`, `Review`, `ChangeSet`, `ReviewCycle` are as listed above.

#### `build soup`

| Field | Type | Meaning |
|---|---|---|
| `manifests_parsed` | list of strings | The manifests it read |
| `packages_found` | integer | Packages across them |
| `to_update` | list of `SoupDrift` | SOUP items whose version has drifted |
| `orphans` | list of `SoupOrphan` | SOUP items no manifest resolves |
| `items_created` | list of strings | SOUP items it wrote, in the working tree |
| `errors` | list of strings | Manifests or commands that could not be read; any exits 1 |

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
| `version` | string | The version released |
| `cr_ids` | list of strings | The completed CRs it includes |
| `rel_uid` | string or null | The REL item recorded; null without `--write` or when a check failed |
| `soup_count` | integer | SOUP items in the BOM |
| `artifacts` | list of strings | Files written under `--out-dir`, relative to it |
| `errors` | list of strings | What blocked the release; any exits 1, and a failing release still writes its evidence |
| `warnings` | list of strings | What it noticed without blocking, such as a component with no purl |

#### `build approvals`

| Field | Type | Meaning |
|---|---|---|
| `version` | string | The release the sheet is for |
| `path` | string or null | The sheet written; null when the release is not fully signed |
| `documents` | integer | Documents on the sheet, the release itself included |
| `signatures` | integer | Signature records the sheet shows |
| `errors` | list of strings | Why no sheet was written, as `verify approval --release` reports it; any exits 1 |
| `warnings` | list of strings | What `verify approval --release` noticed, such as a signature made without proven presence |

#### `build validation`

| Field | Type | Meaning |
|---|---|---|
| `result` | `passed` · `failed` · `incomplete` | `failed` when a point failed or an installed file differs; `incomplete` when a point did not run, the build has no release record or the install cannot be checked. Only `passed` exits 0 |
| `path` | string or null | The report written; null when it could not be rendered |
| `errors` | list of strings | Why the result is not `passed` |

#### `init`

| Field | Type | Meaning |
|---|---|---|
| `project_name` | string | The name written into `global.yaml` |
| `project_dir` | string | Where the project was scaffolded |
| `created` | list of strings | Files created, relative to `project_dir` |
<!-- END GENERATED: shapes -->

---

## Stability

What a caller may rely on:

- **The five envelope keys.** New keys may be added at the top level; existing ones will not be removed or change type without a major version.
- **Exit code meanings.**
- **The commands and their options.** A new one is announced in the changelog; a renamed or removed one is a breaking change.
- **The fields of each report**, as above.
- **The item file format**, described in [configuration.md](configuration.md#items-from-another-system).
- **Not stable:** stderr, and the exact wording of `errors`, `warnings` and `summary`, which are written for a person.

Changes to any of the stable items are called out as breaking in the changelog.
