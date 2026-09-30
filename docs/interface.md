# Interface

> **Stability:** Stable
> **Last reviewed:** 2026-09-30

What a script, a CI pipeline or a coding agent can rely on when it calls `medharness`: what each command does, what it prints, how it exits, and what may change. Tests check the facts stated here against the CLI.

MedHarness does not scaffold a CI workflow — a pipeline carries your runner labels, secrets and branch names, and a generated one would be wrong for most projects. This document is the other half of that decision: build the pipeline against it.

---

## The commands

| Command | What it does | Answers with |
|---|---|---|
| `item list` · `get` · `create` · `update` · `transition` | Reads or changes one DHF item at a time | the item — see [Records](#records-item) |
| `verify dhf` · `tests` · `soup` · `completion` · `changes` | Judges the DHF, and a change against it. Writes nothing | the [result envelope](#the-result-envelope) |
| `build plan` · `code` | An AI drafts a change request's design, or its code | a run report — see [Build](#build); `--prompt` prints Markdown instead |
| `build soup` | Reconciles SOUP items with dependency manifests | a report |
| `build release` | Checks the DHF and writes the release evidence | a report |
| `init` | Scaffolds `DHF/`, `AGENTS.md` and `CLAUDE.md` | `project_name`, `project_dir`, `created` |

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

| Gate | Reads | Needs | Network | Blocking |
|------|-------|-------|---------|----------|
| `verify dhf` | the DHF | — | no | `conditional` |
| `verify tests` | the DHF, JUnit results | `--junit` | no | `conditional` |
| `verify soup` | the DHF, dependency manifests | — | osv.dev | `conditional` |
| `verify completion` | the DHF | `--cr` | no | `always` |
| `verify changes` | the DHF, the working tree's diff | `--cr` | no | `always` |

Every check answers from the machine it runs on, and none reads GitHub. Approval is not a check: GitHub's branch protection — required approvals, stale approvals dismissed on push — enforces it, on the server, where a pull request cannot edit the rule away.

The table is checked against the checks the CLI registers, so it cannot list one that does not exist or omit one that does.

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

| Key | Type | Meaning |
|-----|------|---------|
| `gate` | string | The command that produced this, e.g. `verify tests` |
| `passed` | boolean | Whether the check is satisfied. Always agrees with the exit code |
| `summary` | string | One line, never empty |
| `errors` | list of strings | What made the check fail. Empty when `passed` is true |
| `warnings` | list of strings | What the check noticed without failing |

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

- `verify dhf` — schema errors, required-link failures and dangling links always fail. Coverage gaps warn unless `--strict`.
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

`build` commands are not checks and do not answer with the envelope.

- **`build plan` and `build code`** answer with a run report that includes `cr_id`, `stage`, `outcome` (`ok`, `corrected`, `completed_with_errors` or `tool_error`), `summary`, `artifacts` (`items_changed` or `files_changed`: the branch against `origin/main`, committed or not), `steps`, `warnings` and `errors`. Each entry in `errors` is an object with `field`, `issue` and `fix`. Exit `1` for the last two outcomes. Their execution boundary is in [ai-security.md](ai-security.md).
- **`--prompt`** on either prints Markdown, not JSON: the stage's steps and the CR's DHF context, for an agent that is already running. It starts no model and changes nothing. It is the only output that is not JSON.
- **`build soup`** answers with `outcome`, `to_create`, `to_update`, `orphans`, `items_created`, `items_updated` and `errors`, and always writes the SOUP items in the working tree. Exit `1` on `completed_with_errors`.
- **`build release`** answers with `outcome`, `version`, `cr_ids`, `rel_uid`, `soup_count`, `artifacts`, `errors` and `warnings`. Exit `1` when any check failed; a failing release still writes its evidence to `--out-dir`, so you can read why, but records no REL item.

---

## The item format — integrating another system

Every command reads one thing: YAML files under `DHF/items/`. That format is the integration surface. A team whose requirements live in another tool exports them into it and runs the same commands; there is no plugin to write.

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
| Links | Fields of format `relationship` or `item_multiselect`: a list of IDs pointing up the V-model. Which are required is `required_traceability` in `global.yaml` |
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
