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
    IMPL --> GATES["Verification gates<br/><br/>verify dhf<br/>verify tests<br/>verify soup<br/>verify completion"]
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
      - run: pip install medharness==0.22.0
      - run: medharness --dhf DHF verify dhf --fail-on-uncovered
```

Drop `--fail-on-uncovered` while backfilling an existing DHF: coverage gaps then
report as `WARN`, and only schema, required links, and dangling links block.

`medharness gates` lists every gate with what it requires and whether it blocks.
[docs/interface.md](docs/interface.md) is the contract to build against — result
shape, exit codes, and what may change.
[docs/adopting.md](docs/adopting.md#setting-up-ci) carries the full workflow
with evidence bundles and release baselines.

---

## Commands

`dhfkit` owns DHF **data** — storage and retrieval. `medharness` owns the
**process** around it, including all analysis over the item set. A team whose
DHF already lives in Jira or Azure DevOps keeps that and still needs the
analysis.

Every `dhfkit` command needs the DHF path — pass `--dhf DHF`, or set
`COMPLIANTFLOW_DHF=DHF` once. `medharness` takes `--dhf DHF` and reads no
environment variable.

| | |
|---|---|
| `dhfkit item list --type SYS` | list items; `item get`, `item create`, `item update` for one |
| `dhfkit validate schema` | schema conformance |
| `medharness verify dhf` | do the links resolve — storage integrity |
| `dhfkit doc generate SYS` | build a specification from the items |
| `dhfkit doc export SYS` | self-contained HTML, or PDF with `[docs]` |
| `medharness analyse soup-drift --manifest <file>` | sync SOUP items from a dependency manifest |
| `dhfkit sbom` | CycloneDX 1.6 SBOM from the SOUP register |
| `medharness release baseline --version 1.0.0` | frozen release record |
| `medharness change plan --cr CR-034` | AI drafts DHF items and impact analysis |
| `medharness change implement --cr CR-034` | AI writes code and tests (`--pr 42` to revise from feedback) |
| `medharness verify dhf` | coverage, cycles, dangling links, required traceability |
| `medharness verify tests --junit-dir test-results` | requirement-to-test coverage from JUnit |
| `medharness verify soup` | CVE scan against the OSV database |
| `medharness verify completion` | CR closure gate |
| `medharness verify branch --cr CR-034` | the branch carries the items the CR proposed |
| `medharness verify classification` | IEC 62304 §4.3 safety class and the §5.1 plans it requires |
| `medharness verify verification` | every requirement has a declared verification method |
| `medharness evidence bundle --out-dir artifacts` | runtime evidence for a release |
| `medharness upgrade` | update the scaffold without touching your content |

`medharness gates` and `--help` on any subcommand carry the full surface.

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
