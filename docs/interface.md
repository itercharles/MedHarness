# Machine interface

> **Stability:** Stable
> **Last reviewed:** 2026-09-26

Every verification gate is a command you can call from a pipeline, a script, or an agent. This is the contract those callers build against: one result shape, defined exit codes, and a statement of what may change.

MedHarness deliberately does not scaffold a CI workflow — a pipeline carries your runner labels, secrets, and branch names, and a generated one would be wrong for most projects. This document is the other half of that decision.

---

## The gates

| Gate | Reads | Needs | Network | Blocking |
|------|-------|-------|---------|----------|
| `verify dhf` | the DHF | — | no | `conditional` |
| `verify tests` | the DHF, JUnit results | `--junit-dir` or `--junit` | no | `conditional` |
| `verify soup` | the DHF, dependency manifests | — | osv.dev | `conditional` |
| `verify completion` | the DHF | `--cr` | no | `always` |
| `workflow check-changes` | the DHF, the git diff | `--cr` | no | `always` |
| `workflow check-approval` | the pull request's reviews | `--cr`, `--pr` | GitHub | `always` |

`verify *` answers from the DHF alone, so it runs anywhere the DHF is. `workflow *` cannot answer without the repository; those are CI helpers. Every command takes `--dhf PATH` before the command name, defaulting to `DHF`.

The table is checked against the gates the CLI registers, so it cannot list one that does not exist or omit one that does.

---

## The result envelope

**stdout carries exactly one line of JSON.** Every gate answers with the same five keys:

```json
{
  "gate": "verify tests",
  "passed": false,
  "summary": "1/3 requirement(s) covered by passing tests.",
  "errors": ["SYS: 0/1 requirements covered"],
  "warnings": ["SRS-001: no verification_method declared — pass --require-method to block on this"]
}
```

| Key | Type | Meaning |
|-----|------|---------|
| `gate` | string | The command that produced this, e.g. `verify tests` |
| `passed` | boolean | Whether the gate is satisfied. Always agrees with the exit code |
| `summary` | string | One line, never empty |
| `errors` | list of strings | What made the gate fail. Empty when `passed` is true |
| `warnings` | list of strings | What the gate noticed without failing |

`errors` and `warnings` are **strings already phrased for a reader**, and they are the whole of what the gate found — a caller that prints them produces a usable report without knowing which gate it ran. There is no structured second copy: gates used to carry one under `details`, no caller ever read it, and the documentation of its shape was wrong in three places by the time it was removed.

`summary` is where "what was checked" lives — `13 item(s) checked` distinguishes a real pass from a gate that examined nothing.

A gate that fails always populates `errors`. That is enforced by the test suite across every gate, not by convention — a `passed: false` with nothing to act on is a defect.

---

## Exit codes

| Code | stdout | Meaning |
|------|--------|---------|
| `0` | JSON | Gate passed |
| `1` | JSON | Gate ran and failed — see `errors` |
| `1` | *empty* | The gate never ran: e.g. a DHF that could not be read |
| `2` | *empty* | Argument parsing error, e.g. an unknown flag |

A pipeline that only checks exit status is a valid consumer and needs to parse nothing — which is how the reference project consumes these.

**If you parse, check stdout is non-empty first.** Exit `1` means either a finding or a usage problem, and only the first writes JSON. Treating an empty stdout as parseable is the one mistake this interface invites:

```python
line = proc.stdout.splitlines()
if not line:                      # usage error — the gate never ran
    raise SystemExit(proc.stderr)
result = json.loads(line[0])
```

---

## What blocks a build

The `Blocking` column above means:

| Value | Meaning |
|-------|---------|
| `always` | Any finding fails the gate |
| `conditional` | Some findings always fail; others only under a flag |

For the `conditional` gates, which findings fail and which only warn:

- `verify dhf` — schema errors, required-link failures and dangling links always fail. Coverage gaps warn unless `--fail-on-uncovered`.
- `verify tests` — uncovered requirements and unverified tests always fail. A missing `verification_method` warns unless `--require-method`.
- `verify soup` — known vulnerabilities always fail, and so does an unreachable osv.dev unless `--offline-mode warn`. Drift from the manifests warns unless `--fail-on-drift`.

One distinction worth knowing before you wire anything. **Broken references versus incomplete design:** `verify dhf` always fails on a link whose target does not exist — that is a typo or a deleted item. An item with no downstream child yet is normal mid-project and only fails under `--fail-on-uncovered`. They need different fixes, so they are reported differently.

---

## Stability

What a caller may rely on:

- **The five envelope keys** are stable. New keys may be added at the top level; existing ones will not be removed or change type without a major version.
- **Exit code meanings** are stable.
- **stderr is not a contract.** It is written for a person and its wording changes freely. Never parse it — the same information is in `errors` and `warnings`.
- **The set of gates.** A new gate is announced in the changelog; a renamed or removed one is a breaking change.

Changes to any of the stable items are called out under **Breaking Changes** in the changelog.

---

## Consuming it

### From a pipeline

The simplest correct consumer checks exit status and lets stderr reach the log:

```yaml
- name: DHF gates
  run: |
    medharness --dhf DHF verify dhf --fail-on-uncovered
    medharness --dhf DHF verify tests --junit-dir test-results
    medharness --dhf DHF verify soup
```

To turn findings into annotations, read the envelope:

```bash
medharness --dhf DHF verify dhf --fail-on-uncovered > result.json || true
jq -r '.errors[] | "::error::\(.)"' result.json
jq -r '.warnings[] | "::warning::\(.)"' result.json
exit "$(jq -r 'if .passed then 0 else 1 end' result.json)"
```

### From an agent or a script

Because every gate answers alike, one loop covers all of them:

```python
import json, subprocess

GATES = [
    ["verify", "dhf", "--fail-on-uncovered"],
    ["verify", "tests", "--junit-dir", "test-results"],
    ["verify", "soup"],
]

for gate in GATES:
    proc = subprocess.run(["medharness", *gate], capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    if not lines:                 # the gate never ran
        raise SystemExit(f"{' '.join(gate)}: {proc.stderr.strip()}")
    result = json.loads(lines[0])
    if not result["passed"]:
        report(result["gate"], result["errors"])
```

---

## The item format — integrating another system

The gates read one thing: YAML files under `DHF/items/`. That format is the
integration surface. A team whose requirements live in another tool exports them
into it and runs the same commands; there is no plugin to write.

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
| Fields | Only those the doc type declares. An undeclared field fails `dhfkit validate`, naming it — declare it by overriding the doc type first |
| Links | Fields of format `relationship` or `item_multiselect`: a list of IDs pointing up the V-model. Which are required is `required_traceability` in `global.yaml` |
| Types | The 13 defaults, plus any `DHF/config/doc_types/<type>.yaml` of your own, which replaces the default of that code — see [adopting.md](adopting.md#changing-the-defaults) |

Check an export in two steps: `dhfkit validate` for the files, then
`medharness verify dhf` for the design they describe.

The format is covered by `CONTRACT_VERSION`: renaming or removing a field the
defaults declare is a breaking change.

---

## Event context for a workflow

`medharness workflow github-event --github-output "$GITHUB_OUTPUT"` writes the
CR context straight to a job's outputs:

```
cr_id  mode  pr_number  stage  action  event_name  branch_ref  issue_number
```

A value is written only when it is known, so a downstream `if:` sees an absent
output rather than an empty string. **Do not re-read these through a file and
`jq -r '.field // ""'`** — that turns a failed parse into an empty value that
flows onward and makes every dependent job skip silently, which reads as a green
run that did nothing.

`issue_number` is the issue the pull request closes, read from a closing keyword
(`Closes #88`, `Fixes #13`) in the body carried by the payload. A bare `#12` is a
reference, not a link, and is not reported. **An issue linked through the GitHub
UI leaves no trace in the payload**, so an absent `issue_number` means "not
derivable here", not "there is none" — a workflow that needs those cases still
has to ask the API.

---

## Beyond the gates

`dhfkit` follows the same output convention for DHF data operations — item CRUD, schema validation, document generation, the SBOM — but those commands predate the envelope and keep their own result shapes. Read `--help` for the command you need. `dhfkit` has no dependency on `medharness`, so a project that wants only the engine can use it alone; see [adopting.md](adopting.md#using-dhfkit-standalone).

The `build` commands are not gates and do not answer with the envelope. `build plan` and `build code` report progress and outcomes in their own shape, documented in [adopting.md](adopting.md#ai-assisted-cr-workflow), and their execution boundary is described in [ai-security.md](ai-security.md).
