# Machine interface

> **Stability:** Stable
> **Last reviewed:** 2026-08-26

Every verification gate is a command you can call from a pipeline, a script, or an agent. This is the contract those callers build against: one result shape, defined exit codes, and a statement of what may change.

MedHarness deliberately does not scaffold a CI workflow — a pipeline carries your runner labels, secrets, and branch names, and a generated one would be wrong for most projects. This document is the other half of that decision.

---

## Discovering what exists

```bash
medharness gates            # for a person wiring a pipeline
medharness gates --json     # for a program
```

The JSON manifest lists every gate with what it checks, the standard clauses it serves, the options it requires, whether it reaches the network, and whether its failure blocks a build. A caller that reads the manifest does not need this document hard-coded into it.

```json
{
  "envelope": ["gate", "passed", "summary", "errors", "warnings", "details"],
  "exit_codes": {
    "0": "gate passed",
    "1": "gate failed; see errors",
    "2": "usage error (bad arguments)"
  },
  "gates": [ { "command": "verify soup", "blocking": "always", ... } ]
}
```

The manifest is checked against the live command tree by the test suite, so it cannot describe a gate that does not exist or omit one that does.

---

## The result envelope

**stdout carries exactly one line of JSON.** Every gate answers with the same six keys:

```json
{
  "gate": "verify plans",
  "passed": false,
  "summary": "Class B: 1 plan(s) written, 0 missing, 3 unchanged.",
  "errors": ["development_plan.md is unchanged from the template — §5.1 requires a plan that is maintained."],
  "warnings": ["integration_plan.md: 6 section(s) still match the shipped template"],
  "details": { "declared": "B", "checked": [...], "unwritten": [...] }
}
```

| Key | Type | Meaning |
|-----|------|---------|
| `gate` | string | The command that produced this, e.g. `verify plans` |
| `passed` | boolean | Whether the gate is satisfied. Always agrees with the exit code |
| `summary` | string | One line, never empty |
| `errors` | list of strings | What made the gate fail. Empty when `passed` is true |
| `warnings` | list of strings | What the gate noticed without failing |
| `details` | object | Gate-specific payload; shape varies by gate |

`errors` and `warnings` are **strings already phrased for a reader**, because the machine-readable form of the same findings is in `details`. A caller that prints them produces a usable report without knowing which gate it ran.

A gate that fails always populates `errors`. That is enforced by the test suite across every gate, not by convention — a `passed: false` with nothing to act on is a defect.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Gate passed |
| `1` | Gate failed — see `errors` |
| `2` | Usage error: bad or missing arguments |

`0`/`1` always agree with `passed`. A pipeline that only checks exit status is a valid consumer and needs to parse nothing — which is how the reference project consumes these.

Code `2` comes from the CLI framework before a gate runs, so there is no JSON on stdout in that case. Distinguish it if you parse: an empty stdout with a non-zero exit is a usage problem, not a finding.

---

## What blocks a build

The manifest gives each gate a `blocking` value:

| Value | Meaning |
|-------|---------|
| `always` | Any finding fails the gate |
| `conditional` | Some findings always fail; others only under a flag |
| `opt_in` | Inert until the project opts in; passes otherwise |

Every `conditional` and `opt_in` gate carries a `blocking_note` saying when — "sometimes blocks" is useless without the condition. The suite asserts that note is present.

Two distinctions worth knowing before you wire anything:

**Broken references versus incomplete design.** `verify dhf` always fails on a link whose target does not exist — that is a typo or a deleted item. An item with no downstream child yet is normal mid-project and only fails under `--fail-on-uncovered`. They need different fixes, so they are reported differently.

**Gates that wait for a safety class.** `verify classification` and `verify plans` warn and exit zero until `software_safety_class` is declared in `global.yaml`. You can add them to a pipeline before deciding the class; they will start doing work when you do.

---

## Stability

What a caller may rely on:

- **The six envelope keys** are stable. New keys may be added at the top level; existing ones will not be removed or change type without a major version.
- **Exit code meanings** are stable.
- **`details` is not stable.** Its shape is specific to each gate and may change in a minor release. Read it for a gate you have looked at, not generically.
- **stderr is not a contract.** It is written for a person and its wording changes freely. Never parse it — the same information is in `errors` and `warnings`.
- **The manifest is the source of truth** for which gates exist and what they require. Prefer reading it over hard-coding a list.

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

Because every gate answers alike, one loop covers all of them — including gates added later:

```python
import json, subprocess

manifest = json.loads(
    subprocess.run(["medharness", "gates", "--json"],
                   capture_output=True, text=True).stdout
)

for gate in manifest["gates"]:
    if gate["needs_network"] and offline:
        continue
    proc = subprocess.run(
        ["medharness", "--dhf", "DHF", *gate["command"].split(), *args_for(gate)],
        capture_output=True, text=True,
    )
    result = json.loads(proc.stdout.splitlines()[0])
    if not result["passed"]:
        report(result["gate"], result["errors"])
```

`args_for` supplies what the manifest says the gate requires — `--cr` for the CR-scoped gates, `--junit-dir` for the ones that read evidence.

---

## Beyond the gates

`dhfkit` follows the same output convention for DHF data operations — item CRUD, validation, document generation, SOUP sync, release baselines — but those commands predate the envelope and keep their own result shapes. Read `--help` for the command you need. `dhfkit` has no dependency on `medharness`, so a project that wants only the engine can use it alone; see [adopting.md](adopting.md#using-dhfkit-standalone).

The AI stages (`change plan`, `change implement`) are not gates and do not answer with the envelope. They report progress and outcomes in their own shape, documented in [adopting.md](adopting.md#ai-assisted-cr-workflow), and their execution boundary is described in [ai-security.md](ai-security.md).
