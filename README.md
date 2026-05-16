# MedHarness

**Design-controlled AI development for medical device software.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

---

## What this is

Building software for a medical device means every requirement, risk, architectural decision, and test has to be traced and documented in a **Design History File (DHF)** — before code ships, and in a form that holds up under FDA or notified body scrutiny.

That's a real documentation burden. Teams spend meaningful engineering time on traceability matrices, impact assessments, and evidence bundles — work that doesn't ship features but is genuinely required to ship regulated products.

MedHarness makes that work AI-assisted without making it ungoverned. It gives Claude a structured role in your DHF workflow — generating design items, implementing code, managing SOUP, building release records — while keeping you in the loop at every approval gate. The agent executes; you decide when to advance.

---

## How it works

Every non-trivial change flows through a **Change Request (CR)** in the DHF. MedHarness runs Claude in two phases, validates the output deterministically, and opens a PR for your review before anything moves forward.

**Phase 1 — Design (`generate-dhf`)**

Claude reads the CR, triages it (duplicate? out-of-scope? too large?), then reads the relevant source modules and reasons top-down through the V-model hierarchy:

```
CR → CRS → SYS → { SYSARCH, RISK, RCM } → SRS → SWDD
```

It writes DHF items via the CLI, validates schema and traceability inline, and finally produces a detailed implementation plan in `implementation_notes` on the CR item. A PR opens for your review — you see the design items and the implementation plan before any code is written.

**Phase 2 — Implementation (`develop-cr`)**

After the design PR is approved, Claude reads `implementation_notes` and the linked DHF items, implements the code, annotates tests with `@links:` requirement IDs, runs `medharness ci test-coverage` to verify every requirement has a passing test, and reconciles any deviations back onto `implementation_notes` and the SWDD items.

At each phase, MedHarness pre-computes DHF context — item lists, traceability graph, coverage gaps — and injects it into Claude's prompt so the agent reasons about your actual DHF rather than guessing. After Claude runs, a deterministic validator checks schema, traceability links, and test annotations, and self-corrects if it can.

---

## Who it's for

- **Medical device software teams** working under IEC 62304, FDA 21 CFR 820.30, or MDR who want AI help that doesn't bypass the process
- **Platform / DevOps engineers** building regulated CI pipelines who need programmatic hooks into DHF validation and evidence generation
- **Startups** bootstrapping a DHF alongside their product without a dedicated RA team writing everything by hand

`dhfkit` — the DHF engine inside MedHarness — also works standalone if you only need YAML-based item storage, traceability graphs, and document generation without the full CR workflow.

---

## Install

```bash
pip install medharness[full]
```

`[full]` includes optional extras: `ai` (AI review) and `docs` (PDF export via WeasyPrint). Leave it off for a minimal install — `dhfkit` is always included either way.

```bash
medharness --help
dhfkit --help
```

**From source:**

```bash
git clone https://github.com/itercharles/MedHarness
cd MedHarness
pip install -e ".[dev]"
pytest dhfkit/tests/ tests/
```

---

## Quick start

`medharness init` scaffolds a complete DHF project in the current directory — no prompts, nothing to fill out:

```bash
mkdir my-device && cd my-device
python -m venv .venv && source .venv/bin/activate
pip install medharness
medharness init
```

You get a working DHF with sample requirements, risks, traceability config, document templates, and plans — ready to replace with your real content:

```
my-device/
├── DHF/
│   ├── config/           # project name, lifecycle states, doc type schemas
│   ├── items/            # one YAML file per requirement, risk, CR, etc.
│   │   ├── 01_crs/       # Customer Requirements
│   │   ├── 02_sys/       # System Requirements
│   │   ├── 03_srs/       # Software Requirements
│   │   ├── 06_cr/        # Change Requests
│   │   └── ...           # Use Cases, SOUP, Risk, RCM, Releases, Defects
│   ├── documents/        # Jinja2 spec templates and plan documents
│   └── test-results/
├── CLAUDE.md             # AI agent entrypoint
└── README.md
```

Then push it to git and you're tracking your DHF from day one:

```bash
git init && git add -A && git commit -m "feat: initialize DHF"
```

---

## The CR workflow in practice

```bash
# Phase 1 — Claude triages the CR, generates DHF items, and writes an
# implementation plan. Opens a PR for design review.
medharness --dhf DHF ci generate-dhf --cr CR-034

# Phase 2 — after the design PR is approved, Claude implements the code,
# verifies test coverage, and reconciles any deviations back onto the DHF.
medharness --dhf DHF ci develop-cr --cr CR-034
```

Claude reasons top-down through the V-model during design, reading relevant source modules before writing SWDD items so the reviewed design reflects the actual codebase. The implementation plan in `implementation_notes` is the handoff artifact — it drives the develop phase without re-deriving the design.

Got review comments on a design PR? Pass `--pr N` to revise based on the feedback:

```bash
medharness --dhf DHF ci generate-dhf --cr CR-034 --pr 42
medharness --dhf DHF ci develop-cr --cr CR-034 --pr 42
```

`ANTHROPIC_MODEL` selects the Claude model. `GH_TOKEN` is required when using `--pr`.

Each command outputs structured JSON with outcome, errors, timing, and artifact paths — so CI automation can act on results without parsing text.

---

## CR lifecycle

A CR moves through these states as the workflow progresses:

| State | Meaning |
|-------|---------|
| `new` | CR created, awaiting design |
| `design` | `generate-dhf` has run; design PR open for review |
| `develop` | Design approved; `develop-cr` has run; code PR open |
| `completed` | Code PR merged |
| `cancelled` | PR closed without merging |
| `rejected` | Triage determined the CR is out-of-scope, duplicate, or too large |

States are recorded for traceability and audit. Only `completed` CRs may be included in a release baseline — `cancelled` and `rejected` CRs are not deliverables.

---

## CI gates

### DHF schema and traceability

```bash
medharness ci dhf-validate --dhf DHF
```

Validates item schemas, required fields, and traceability links across the entire DHF.

### Requirement-to-test coverage

```bash
medharness ci test-coverage --dhf DHF --junit-dir test-results
```

Reads JUnit XML test results and checks that every verifiable requirement has at least one linked passing test. Tests link to DHF items via `@links:<ITEM_ID>` annotations in their source, surfaced through JUnit properties. Exits non-zero when gaps exist.

### Branch and code validation

```bash
# Verify the CR's design items and traceability are complete before merging
medharness --dhf DHF ci validate-branch --cr CR-034

# Run deterministic implementation validation (schema + coverage) without Claude
medharness --dhf DHF ci validate-code --cr CR-034
```

### Evidence bundle

```bash
medharness ci evidence bundle --dhf DHF --out-dir artifacts --junit-dir test-results
```

Produces a timestamped DHF snapshot and test evidence archive, typically run on merge to `main`.

### Approval gating and stage management

```bash
# Guard against acting on the wrong event — check that a stage has an explicit approval
medharness ci approve-gate --cr CR-034 --stage design --pr 42

# Report machine-readable CR stage and label state (for routing in CI)
medharness --dhf DHF ci cr-status --cr CR-034 --pr 42

# Advance the stage label on a PR (removes old label, adds new one, idempotent)
medharness ci advance-stage --pr 42 --from-stage design --to-stage develop

# Parse a PR comment for /approve or /reject commands
medharness ci parse-approval --comment "$COMMENT_BODY"
```

---

## SOUP management and release baseline

### SOUP synchronisation (IEC 62304 §5.3.3)

`ci soup-sync` reads your package manifests and diffs them against SOUP items already in the DHF, reporting new dependencies, version drift, and orphaned records.

```bash
# Dry-run: show what would change
medharness --dhf DHF ci soup-sync \
  --manifest requirements.txt \
  --manifest apps/client/package.json

# Apply creates and updates
medharness --dhf DHF ci soup-sync \
  --manifest requirements.txt \
  --write --author "ci" --cr CR-034
```

Supports `requirements.txt` (pinned `==` entries only) and `package.json` (`dependencies`, `devDependencies`, `peerDependencies`). Fuzzy name matching handles hyphen/underscore/case variants; duplicate packages across manifests are deduplicated automatically.

### Release baseline (IEC 62304 §9)

`ci release-baseline` verifies that all included CRs are completed, collects a software BOM from DHF SOUP items and package manifests, and writes `release-baseline.json` and `software-bom.json` to `--out-dir`.

```bash
# Dry-run: auto-collect completed unreleased CRs, write artifacts
medharness --dhf DHF ci release-baseline \
  --version 1.0.0 \
  --manifest requirements.txt \
  --out-dir artifacts/release

# Explicitly specify CRs and create a REL item in the DHF
medharness --dhf DHF ci release-baseline \
  --version 1.0.0 \
  --cr CR-030 --cr CR-031 --cr CR-034 \
  --manifest requirements.txt \
  --out-dir artifacts/release \
  --write --author "ci"
```

When `--cr` is omitted, all completed CRs not yet referenced in any existing REL item are collected automatically. The gate exits non-zero if any specified CR is not in `completed` state.

---

## Automation model

MedHarness ships no prescribed CI workflow files — the stable interface is the CLI. Wire it into whatever automation layer fits your team (GitHub Actions, GitLab CI, Jenkins, local scripts):

```bash
# ── DHF operations ──────────────────────────────────────────────────────────
medharness --dhf DHF dhf item list --type SYS
medharness --dhf DHF dhf item get CR-034
medharness --dhf DHF dhf item transition CR-034 completed --by "alice"
medharness --dhf DHF dhf validate schema
medharness --dhf DHF dhf validate traceability
medharness --dhf DHF dhf doc generate SYS
medharness --dhf DHF dhf doc export SYS            # PDF (requires [docs])
medharness --dhf DHF dhf report                    # human-readable traceability coverage
medharness --dhf DHF dhf context implementation \  # AI/CI context bundle for a CR
  --cr CR-034 --out-dir /tmp/ctx

# ── AI-assisted CR workflow ──────────────────────────────────────────────────
medharness --dhf DHF ci generate-dhf --cr CR-034   # design phase
medharness --dhf DHF ci develop-cr --cr CR-034     # implement phase

# ── SOUP and release ─────────────────────────────────────────────────────────
medharness --dhf DHF ci soup-sync --manifest requirements.txt
medharness --dhf DHF ci release-baseline --version 1.0.0 --out-dir artifacts/release

# ── CI gates ─────────────────────────────────────────────────────────────────
medharness ci dhf-validate --dhf DHF
medharness ci test-coverage --dhf DHF --junit-dir test-results
medharness ci evidence bundle --dhf DHF --out-dir artifacts
medharness --dhf DHF ci validate-branch --cr CR-034
medharness --dhf DHF ci validate-code --cr CR-034

# ── Observability and event routing ──────────────────────────────────────────
medharness --dhf DHF ci cr-status --cr CR-034 --pr 42
medharness ci approve-gate --cr CR-034 --stage design --pr 42
medharness ci advance-stage --pr 42 --from-stage design --to-stage develop
medharness ci parse-approval --comment "$COMMENT_BODY"
medharness ci github-event --event "$GITHUB_EVENT_PATH"
```

---

## Python API

```python
from medharness.client import DHFClient

client = DHFClient(Path("DHF"))
cr   = client.get_item("CR-034")
client.transition_item("CR-034", "completed", performed_by="alice")
```

`dhfkit` standalone — no dependency on `medharness`:

```python
from dhfkit.local_adapter import LocalDHFAdapter

adapter = LocalDHFAdapter(Path("DHF"))
items   = adapter.list_items("SRS")
```

---

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `medharness/` | CLI harness, CI gates, CR workflows, `init` scaffolding |
| `dhfkit/` | DHF engine: items, lifecycle, traceability, document generation |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, sample items |
| `tests/` | MedHarness and dhfkit test suites |
| `docs/` | Architecture, ADRs, compatibility contracts |

`dhfkit` has no dependency on `medharness` and can be used on its own.

---

## Docs

- [docs/architecture.md](docs/architecture.md) — packages, scaffold model, DHF lifecycle
- [docs/compatibility-contracts.md](docs/compatibility-contracts.md) — stable public contracts
- [docs/adr/](docs/adr/) — architecture decision records
- [CHANGELOG.md](CHANGELOG.md) — version history

---

## License

MIT — see [LICENSE](LICENSE).
