# MedHarness

**AI coding harness for teams shipping software under design control.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

AI can write the code. It cannot tell you which requirement the change serves,
which risk it touches, or whether the traceability still holds — and under IEC
62304 those are the parts that decide whether the work counts.

MedHarness closes that gap. It reads the design behind a change request, drives
the implementation from it, then checks the result against the design again with
ordinary code — no model is asked whether the work is done.

---

## What only it can tell you

Your issue tracker manages one item well. It cannot take every item together and
ask whether the V-model still holds — whether each requirement gives rise to the
next, whether a chain closes back on itself, which risks a change touches. That
analysis is what MedHarness is for, and it reads items as data, so it works
whether they live in YAML here or in Jira.

```console
$ medharness --dhf DHF verify dhf
FAIL [cycle] SRS-014 → SYS-006 → SRS-014
    Fix: the V-model is directed. Remove whichever link reverses the chain so each item has an origin.
FAIL [required] SRS-022: SRS derives_from → SYS (count=0, need ≥1)
WARN [coverage] RISK→RCM: 3/4 covered
    Fix: dhfkit --dhf DHF item list --type RCM to find uncovered items, then add dhf_links to their YAML.
         Advisory only — pass --fail-on-uncovered to block the build on this.
Error: DHF validation failed.
```

A cycle means two items each derive from the other, so neither has an origin and
the matrix loses the direction that makes it a matrix. A missing required link
means a requirement traces to nothing above it. Both are structural — they block.

Incomplete design (`WARN`) blocks only under `--fail-on-uncovered`, because it is
design still to be written. Conflating the two is what makes traceability checks
something teams learn to ignore.

Storage-level checks — schema, and links whose target does not exist — come from
`dhfkit` and run in the same pass. A backend that enforces referential integrity
of its own makes them redundant; the analysis above it does not go away.

---

## How a change moves

Every change is a Change Request on a fixed path. AI drafts, humans approve,
deterministic gates decide whether it can close.

```mermaid
flowchart LR
    CR["CR-042<br/>opened"] --> PLAN
    PLAN["change plan<br/><br/>AI drafts DHF items<br/>and impact analysis"] --> REV{"Human<br/>review"}
    REV -.->|rejected| PLAN
    REV -->|"/approve"| IMPL["change implement<br/><br/>AI writes code<br/>and tests"]
    IMPL --> GATES["Verification gates<br/><br/>verify dhf<br/>verify tests<br/>verify soup<br/>change verify-completion"]
    GATES -.->|any gate fails| IMPL
    GATES ==>|all pass| MERGE["Merge to main<br/><br/>evidence bundle<br/>release baseline"]

    style PLAN fill:#4c6ef5,color:#fff,stroke:#364fc7
    style IMPL fill:#4c6ef5,color:#fff,stroke:#364fc7
    style REV fill:#f59f00,color:#fff,stroke:#e67700
    style GATES fill:#f1f3f5,color:#212529,stroke:#868e96
    style MERGE fill:#2f9e44,color:#fff,stroke:#2b8a3e
```

Only the blue steps call a model. Everything in the verification band is
ordinary code. See [docs/ai-security.md](docs/ai-security.md) for the boundary
in detail — including how to run with no AI at all.

---

## Install

```bash
mkdir my-device && cd my-device
python -m venv .venv && source .venv/bin/activate
pip install medharness
medharness init
```

`medharness init` scaffolds `DHF/` (config, items, documents), `AI-harness/`,
and prompt templates. Extras: `medharness[ai]` for the AI workflow,
`medharness[docs]` for PDF export, `medharness[full]` for both.

Check the environment at any point:

```bash
medharness doctor
```

### Before enabling the AI stages

`change plan` and `change implement` need a model CLI or API key, which pip
cannot install:

```bash
npm install -g @anthropic-ai/claude-code   # default path, provides the `claude` CLI
```

**Read [docs/ai-security.md](docs/ai-security.md) first.** These stages run an
agentic loop with an unrestricted shell tool and are designed for an ephemeral
CI runner, not a workstation holding your credentials.

Everything else — traceability, validation, gates, evidence bundles — is
deterministic and needs no model access.

---

## First change request

```bash
git init && git add -A && git commit -m "feat: initialize DHF"

# Edit DHF/items/07_cr/CR-001.yaml, then:
medharness --dhf DHF change plan --cr CR-001       # AI drafts DHF items + impact analysis
# review and approve the design PR, then:
medharness --dhf DHF change implement --cr CR-001  # AI writes code and tests
medharness --dhf DHF verify dhf                    # gates decide whether it can close
```

---

## Deploy to CI

MedHarness does not install a CI workflow — it would reference your branch
names, runners, and secrets, and `medharness upgrade` will never overwrite it.
Pin the version and call the gates:

```yaml
name: DHF
on:
  pull_request:
    paths: ['DHF/**']

jobs:
  dhf-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install medharness==0.26.3
      - run: medharness --dhf DHF verify dhf --fail-on-uncovered
```

Drop `--fail-on-uncovered` while backfilling an existing DHF: coverage gaps then
report as `WARN`, and only schema, required links, and dangling links block.

`medharness verify --help` lists the gates; each subcommand's `--help` gives its options.
[docs/interface.md](docs/interface.md) is the contract to build against — result
shape, exit codes, and what may change.
[docs/adopting.md](docs/adopting.md#setting-up-ci) carries the full workflow
with evidence bundles and release baselines.

---

## Commands

`dhfkit` owns DHF **data** — storage and retrieval, no analysis. `medharness`
owns the **analysis over the item set** and the process around it. A team whose
DHF already lives in Jira or Azure DevOps keeps that and still needs the
analysis.

Both take `--dhf DHF`; `dhfkit` also reads `COMPLIANTFLOW_DHF`.
Every command writes JSON to stdout and human-readable lines to stderr, so
`cmd > out.json` gives you the payload and the terminal still reads normally.

**Gates** — `verify *` and `change verify-*` — all answer with the same
envelope, so one CI step can handle any of them:

```json
{"gate": "verify dhf", "passed": false, "summary": "FAIL — 1 link cycle(s)",
 "errors": ["..."], "warnings": ["..."], "details": {}}
```

`0` the gate passed · `1` it failed (JSON on stdout) or a usage error was raised
before it ran (no stdout) · `2` argument parsing failed.

So the verdict is always `passed` and the exit code — that is what a CI step
branches on. The tables below say what each gate puts in `details`, which is the
only part that differs between them: a gate that answered `false` and nothing
else could not be acted on, and §62304 evidence records what was checked, not
just the verdict.

### Gates on the DHF — no CR needed

Run these on any DHF, whether or not the project uses the AI change workflow.

| Command | `details` carries | Use it when |
|---|---|---|
| `medharness verify dhf` | `results.schema` — is the data readable at all, checked first because the rest is only true if it is. `results.traceability` — four separate questions, because each has a different fix: `required` (a mandatory link is absent), `dangling` (a link names an item that does not exist), `cycles` (two items each derive from the other, so neither has an origin), `coverage` (per parent→child pair, how many are covered and which are not). Plus `results.verification_gaps` — items that state no verification criterion. | Every push. This is the one gate a DHF cannot do without: it is the only check that reads the items *together* and asks whether the V-model closes. |
| `medharness verify tests --junit-dir test-results` | `missing_method`, `unverified_test`, `manual_review_required` | After the test job, to prove each requirement was verified **by the method it declared** — a Test-verified requirement needs a passing linked test, not just any evidence. |
| `medharness verify soup --manifest requirements.txt` | `drift` — the register against the manifests, split by how it diverged (`undocumented`, `no_longer_shipped`, `misversioned`, `undescribed`). `vulnerable` — OSV matches. `accepted` — CVEs this project has documented a decision on, and `acceptance_problems` where that record is unusable. | Nightly and before a release. Answers both §8.1.2 questions at once: is the register what actually ships, and is any of it known-vulnerable. `--offline-mode warn` for air-gapped runners. |
| `medharness verify classification` | `classification.declared` — the class set in global.yaml, empty until you set one. `classification.rationale_present`, `classification.missing_item_types` — the item types this class requires that the DHF has none of. `plans.declared` / `plans.checked` — the §5.1 plans the class calls for, and which were found. | Once a safety class is declared, to check the §5.1 plans that class requires exist. Warns and exits 0 until you declare one, so it is safe to wire before you have decided. |

### Gates on a change request

These read fields `change plan` writes, so they apply only to a project running
the CR workflow. A PR with no CR passes them.

| Command | `details` carries | Use it when |
|---|---|---|
| `medharness change verify-branch --cr CR-034` | `promised_but_unchanged`, `cr_found`, `findings` | On the PR. Checks the branch actually changed the items the CR listed in `affected_items` — a CR that promised to touch SYS-001 and did not is caught before review, not after. |
| `medharness change verify-completion --cr CR-034 --junit-dir test-results` | `incomplete_cr_fields`, `missing_items`, `verification_gaps`, `unverified_test`, `manual_review_required` | Twice. On the branch to block the merge — the CR fields, the approval and the proposed items settle there. Again on `main`, where the tests re-run against whatever else landed. Reports only items **this CR** touched. |
| `medharness change verify-approval --cr CR-034 --stage design --pr 42` | `approved`, `approvals`, `stale_approvals`, `head_sha`, `stage` | Before merging. Requires an approving GitHub review whose commit is the one being merged; an approval of an earlier commit is reported as stale and fails. `--stage` is recorded, not searched on — the commit is what separates design from develop. Needs `GH_TOKEN`. |

### The AI change workflow

| Command | Returns | Use it when |
|---|---|---|
| `medharness change plan --cr CR-034` | `outcome`, `items_changed`, `review_cycles`, `diagnostics` | The CR has been triaged. Drafts the whole DHF item cascade and the impact analysis, then validates its own output and fixes what it broke. |
| `medharness change implement --cr CR-034` | `outcome`, `files_changed`, `review_cycles` | The design is approved. Writes code and tests against the cascade. `--pr 42` revises from review feedback; `--ci-failures` from a failing run. |
| `medharness automation github-event` | `cr_id`, `stage`, `action`, `pr_number`, `mode`, `reason` | First step of a workflow. Reads the GitHub event and says which CR and stage it concerns and what to do — so the workflow branches on one command's output instead of a ladder of `if` expressions. |

### Context for an agent

All three print JSON to stdout and make no changes.

| Command | Returns | Use it when |
|---|---|---|
| `medharness context overview` | `project`, `item_count`, `items`, `traceability`, `test_coverage` | An agent or a person is new to the DHF. `traceability.valid` is the same verdict `verify dhf` reaches. Pass `--junit-dir` to get real test coverage instead of `{"computed": false}`. |
| `medharness context implementation --cr CR-034` | `project`, `cr` (the full item), `items`, `traceability`, `module_map` | An agent is about to write code for a CR: which modules own which designs and requirements. |
| `medharness context for-stage develop --cr CR-034` | `stage`, `cr`, `affected_items` (or `traceability_gaps` at `analyze`) | You want the smaller answer — only what one stage needs, rather than the whole DHF. |

### Evidence and release

| Command | Returns | Use it when |
|---|---|---|
| `medharness evidence bundle --out-dir artifacts` | `gate_passed`, `manifest`, `artifacts` | On merge to `main`. Runs the acceptance gate and writes the read-only bundle an auditor reads: specifications, plans, traceability, test evidence, SBOM, and a manifest with a hash per file. `--doc-format pdf` needs `medharness[docs]`. |
| `medharness release baseline --version 1.0.0 --write` | `version`, `cr_ids`, `rel_uid`, `artifacts`, `soup_count` | Cutting a release (IEC 62304 §9). Verifies every included CR is `completed`, freezes the software BOM, and writes the REL item. Dry-run without `--write`. |
| `medharness soup-sync --manifest requirements.txt --write` | `to_create`, `to_update`, `orphans`, `items_created`, `items_updated` | A dependency changed. Reconciles the SOUP register with the project's manifests. Without `--write` it reports only — read that first: it writes items you then have to fill in a purpose and risk rating for. |

### Setting up and keeping current

| Command | Returns | Use it when |
|---|---|---|
| `medharness init` | list of created paths | Once, in an empty project. Scaffolds the DHF, the AI harness, and a CI workflow. Never overwrites. |
| `medharness upgrade` | `outdated`, `missing`, `up_to_date`, `installed_version` | After upgrading the package. Reports scaffold drift; `--apply` writes it. Your DHF items, `global.yaml` and `context.md` are never touched. |
| `medharness doctor` | `checks`, `passed`, `failed` | CI is behaving oddly. Checks Python, the CLIs, `gh` auth, and whether the DHF config and adapter load. |

### Storing and reading the DHF — `dhfkit`

| Command | Returns | Use it when |
|---|---|---|
| `dhfkit item list --type SYS` | one JSON object per line | Enumerating items of a type. |
| `dhfkit item get SRS-012` | the item, with `all_linked_uids` resolved | You need one item's fields and links. |
| `dhfkit item create --type SRS --data '{...}'` | the created item, with its assigned ID | Adding an item. The ID is allocated for you. |
| `dhfkit item update SRS-012 --data '{...}'` | the updated item | Changing fields. The JSON is merged, not replaced; editing an approved item returns it for re-approval. |
| `dhfkit item transition CR-034 completed` | the item in its new state | Moving an item through its lifecycle. Omit the state to get the transitions available and which criteria block the rest. |
| `dhfkit validate schema` | `valid`, `item_count`, `errors` | Before committing. Every item against its doc-type schema. |
| `dhfkit doc generate SYS` | `doc_type`, `output_path`, `version` | Building a specification document from the items. |
| `dhfkit doc export SYS --format pdf` | `output_path` | Handing a specification to someone outside the repo. HTML is self-contained; PDF needs `[docs]`. |
| `dhfkit sbom` | `path`, `components`, `without_purl` | You need a CycloneDX 1.6 SBOM from the SOUP register. `without_purl` counts the components no tool downstream can match. |
| `dhfkit init` | list of created paths | You want the DHF without the AI harness. |

Attribution is the commit, not a flag: `dhfkit` does not commit, so who changed
an item is whoever authored the commit that carried it.

`--help` on any subcommand carries the full surface.

**Model configuration.** Each stage falls back to the Anthropic Claude CLI
unless you set `MEDHARNESS_{DESIGN,DESIGN_REVIEW,DEVELOP,CODE_REVIEW}_MODEL` to
a `provider:model` value — `anthropic`, `openai` (`OPENAI_API_KEY`), or
`deepseek` (`DEEPSEEK_API_KEY`). `MEDHARNESS_{STAGE}_BASE_URL` points a stage at
Azure, Ollama, or vLLM. `GH_TOKEN` is required for `--pr`.

---

## Seeing it run

[**ContourLab**](https://github.com/itercharles/ContourLab) is a browser-based
contouring workspace for radiation oncology, maintained end-to-end with
MedHarness. Its `DHF/` holds the real design inputs and traceability, every
change goes through the CR path above, and CI runs the gates on every PR. If you
want to read a production adoption before committing to one, start there.

---

## Documentation

| | |
|---|---|
| [docs/adopting.md](docs/adopting.md) | starting fresh, migrating an existing DHF, incremental adoption |
| [docs/interface.md](docs/interface.md) | the machine interface — result envelope, exit codes, stability |
| [docs/ai-security.md](docs/ai-security.md) | what the AI stages can do, isolation, audit trail, no-AI operation |
| [docs/architecture.md](docs/architecture.md) | package boundaries, CR topology, scaffold layout |
| [docs/adr/](docs/adr/) · [CHANGELOG.md](CHANGELOG.md) | decision records; version history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | contributor setup and local development |

`dhfkit` has no dependency on `medharness`, so the DHF engine can be adopted
standalone.

---

## License

MIT. See [LICENSE](LICENSE).
