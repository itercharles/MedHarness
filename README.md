# MedHarness

**Design-controlled AI development for medical device software.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

---

Building software for a medical device means every requirement, risk, architectural decision, and test has to be traced and documented in a **Design History File (DHF)** — before code ships, and in a form that holds up under FDA or notified body scrutiny.

MedHarness makes that work AI-assisted without making it ungoverned. It gives Claude a structured role in your DHF workflow — generating design items, implementing code, managing SOUP, building release records — while keeping you in the loop at every approval gate. The agent executes; you decide when to advance.

---

## Install

```bash
pip install medharness[full]
```

`[full]` includes optional extras: `ai` (AI review) and `docs` (PDF export via WeasyPrint). Leave it off for a minimal install — `dhfkit` is always included either way.

**From source:**

```bash
git clone https://github.com/itercharles/MedHarness
cd MedHarness
pip install -e ".[dev]"
pytest dhfkit/tests/ tests/
```

---

## Quick start

```bash
# 1. Scaffold a new DHF project
mkdir my-device && cd my-device
python -m venv .venv && source .venv/bin/activate
pip install medharness
medharness init
```

`medharness init` gives you a working DHF with sample requirements, risks, traceability config, document templates, and plans:

```
my-device/
├── DHF/
│   ├── config/           # project name, doc type schemas
│   ├── items/            # one YAML file per requirement, risk, CR, etc.
│   │   ├── 01_crs/       # Customer Requirements
│   │   ├── 02_sys/       # System Requirements
│   │   ├── 03_srs/       # Software Requirements
│   │   ├── 07_cr/        # Change Requests
│   │   └── ...           # Use Cases, SOUP, Risk, RCM, Releases, Defects
│   └── documents/        # Jinja2 spec templates and plan documents
├── AI-harness/
│   └── context.md        # Product context for AI agents
└── .github/
    └── workflows/
        └── dhf.yml       # CI: validate on PR, evidence bundle on main
```

Replace the sample items with your own content, then commit:

```bash
# 2. Replace sample content and commit
git init && git add -A && git commit -m "feat: initialize DHF"
```

```bash
# 3. Edit DHF/items/07_cr/CR-001.yaml with your first change request, then run design phase
medharness --dhf DHF ci generate-dhf --cr CR-001
# → Claude triages the CR, generates DHF items, writes an implementation plan, opens a PR
```

```bash
# 4. After the design PR is reviewed and approved, run the implementation phase
medharness --dhf DHF ci develop-cr --cr CR-001
# → Claude implements code, annotates tests, verifies coverage, opens a code PR
```

The scaffolded project includes `.github/workflows/dhf.yml` — a GitHub Actions workflow that runs `dhf-validate` on every DHF PR and produces an evidence bundle on merge to main.

---

## Coming from an existing system

If you have an existing DHF in Excel, Jira, Polarion, or a custom format, migration is writing YAML files — one per requirement, risk, or CR record. MedHarness items map directly to familiar artifact types: requirements spreadsheets become SRS/SYS items, risk registers become RISK + RCM items, SOUP lists become SOUP items.

See [docs/adopting.md](docs/adopting.md) for the full mental model: starting fresh, migrating an existing DHF, using `dhfkit` standalone, and adopting incrementally.

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

## CR workflow

```bash
# Phase 1 — Claude triages the CR, generates DHF items, and writes an
# implementation plan. Opens a PR for design review.
medharness --dhf DHF ci generate-dhf --cr CR-034

# Phase 2 — after the design PR is approved, Claude implements the code,
# verifies test coverage, and reconciles any deviations back onto the DHF.
medharness --dhf DHF ci develop-cr --cr CR-034
```

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

MedHarness ships a minimal GitHub Actions workflow (scaffolded into new projects by `medharness init`). The stable interface is the CLI — wire it into whatever automation layer fits your team (GitHub Actions, GitLab CI, Jenkins, local scripts):

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

- [docs/adopting.md](docs/adopting.md) — starting fresh, migrating an existing DHF, incremental adoption
- [docs/architecture.md](docs/architecture.md) — packages, scaffold model, DHF lifecycle
- [docs/adr/](docs/adr/) — architecture decision records
- [CHANGELOG.md](CHANGELOG.md) — version history

---

## License

MIT — see [LICENSE](LICENSE).
