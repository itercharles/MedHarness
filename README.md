# MedHarness

**AI harness and DHF tooling for medical device software teams.**

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

MedHarness structures how AI agents interact with a Design History File under
IEC 62304 / FDA-regulated software projects. It pre-computes DHF context before
an agent runs, enforces approval gates the agent must pass through, and commits
decisions back into the DHF — so the engineer controls the feedback loop, not
the agent.

It combines two packages:

- **`medharness`** — CLI harness, CI gates, CR workflows, project scaffolding (`init`)
- **`dhfkit`** — standalone DHF engine for items, traceability, document generation, schema validation

---

## Install

```bash
pip install medharness[full]
```

`[full]` pulls in optional extras: `ai` (Gemini-based AI review) and `docs` (PDF export via WeasyPrint).
Omit for a minimal install — the DHF engine (`dhfkit`) is always included.

Verify:

```bash
medharness --help
dhfkit --help
```

**From source (development):**

```bash
git clone https://github.com/itercharles/MedHarness
cd MedHarness
pip install -e ".[dev]"
pytest dhfkit/tests/ tests/
```

---

## Quick Start

`medharness init` interactively scaffolds two repos:

```bash
medharness init
```

You'll be asked for:
- GitHub org/username and product repo name
- Whether to scaffold a DHF repo (recommended: yes)

After `init` completes, here's what exists on disk:

```
my-product-dhf/                      # DHF repo (scaffolded)
├── DHF/
│   ├── config/
│   │   ├── global.yaml             # project name, lifecycle states
│   │   └── doc_types/              # one YAML per type (SYS, CRS, SRS, SWDD, CR, …)
│   ├── items/                      # one YAML file per requirement / risk / CR
│   │   ├── 01_crs/                 # Customer Requirements (CRS-NNN.yaml)
│   │   ├── 02_sys/                 # System Requirements (SYS-NNN.yaml)
│   │   ├── 03_srs/                 # Software Requirements (SRS-NNN.yaml)
│   │   ├── 06_cr/                  # Change Requests (CR-NNN.yaml)
│   │   └── ...                     # Use Cases, SOUP, Risk, Defects, etc.
│   ├── test-results/
│   │   └── results.yaml            # automated test result records
│   ├── documents/
│   │   ├── specs/                  # Jinja2 spec templates (.j2)
│   │   └── plans/                  # development_plan.md, integration_plan.md
│   └── AI-harness/                 # agent context files
├── .github/workflows/              # CR analysis, design, CI validation
└── README.md

my-product/                         # Product repo (minimal files written)
├── CLAUDE.md                       # agent entrypoint
├── .github/workflows/
│   ├── engineering-control.yml     # main CI: test + coverage gate + evidence
│   ├── cr-complete.yml             # auto-close CR on PR merge
│   └── review-pr.yml               # AI-assisted PR review
└── .claude/skills/                  # Claude Code skills (traceability-check, …)
```

The scaffolded items are **starter samples** — replace them with your project's
real requirements, architecture, and plans before using this for a regulated product.

**Push both repos to GitHub and open a PR:**

```bash
# 1. Push the DHF repo
cd my-product-dhf
git init && git remote add origin https://github.com/my-org/my-product-dhf
git add -A && git commit -m "feat: initialize DHF"
git push -u origin main

# 2. Open an engineering control PR in the product repo
cd ../my-product
git checkout -b medharness/setup
git add -A && git commit -m "feat: add MedHarness harness and CI workflows"
git push -u origin medharness/setup
# → open PR, add DHF_REPO_TOKEN secret, merge
```

---

## How a Change Request flows

Every non-trivial change starts as a **Change Request (CR)** in the DHF repo.
CRs move through five AI-assisted stages:

```
Issue → cr-analyze → cr-design → cr-develop → cr-complete
```

| Stage | Trigger | What MedHarness does |
|-------|---------|---------------------|
| **cr-analyze** | Issue labeled `CR` | Pre-computes DHF context, runs Claude to write a technical spec, commits the spec to `docs/cr-specs/` |
| **cr-design** | Spec merged | Reads the approved spec, creates/updates DHF items (SYS, SRS, SWDD, …), validates schema |
| **cr-develop** | Design merged | Clones the DHF, injects `$DHF_CONTEXT`, runs Claude to implement code in the product repo, opens a PR |
| **iterate** | Reviewer comments | Resumes the Claude session with review feedback, pushes revisions |
| **cr-complete** | PR merged | Transitions the CR to `complete` in the DHF, generates closing evidence |

At each stage MedHarness:

1. **Pre-computes context** — `medharness dhf context for-stage <stage>` returns focused JSON
2. **Injects into agent environment** — `$DHF_CONTEXT` is available to Claude
3. **Captures decisions back** — `medharness dhf item transition --commit --push`
4. **Stores session IDs** — `medharness ci claude-session put/get` for iterative review loops

The workflow YAML files for each stage live in the DHF repo under `.github/workflows/dhf/`
and are scaffolded by `medharness init`.

---

## Test Coverage Gate

The CI gate (`medharness ci test-coverage`) enforces that every verifiable requirement
has at least one passing test linked to it.

### JUnit XML contract

Tests must emit JUnit XML with properties linking to DHF item IDs:

```xml
<testcase name="test_TC_SYS_005_001_validates_link_format">
  <properties>
    <property name="medharness.id" value="TC-SYS-005-001"/>
    <property name="medharness.links" value="SYS-005"/>
  </properties>
</testcase>
```

All property names are defined as constants in `medharness/contracts.py`:

| Property | Purpose |
|----------|---------|
| `medharness.id` | Test case identifier (e.g. `TC-SYS-005-001`) |
| `medharness.links` | Comma-separated DHF item IDs the test covers |
| `medharness.title` | Human-readable test title (optional) |
| `medharness.reviewer` | Reviewer name (optional) |
| `medharness.review_date` | Review date (optional) |
| `medharness.review_status` | Review status (optional) |

### Python / pytest

Use pytest's `record_property` in `conftest.py`:

```python
@pytest.fixture(autouse=True)
def _inject_medharness_metadata(request, record_property):
    doc = request.function.__doc__ or ""
    tc_id = extract_tc_id_from_name(request.node.name)
    links = parse_links(doc)   # extract @links:SYS-005 from docstring
    if tc_id:
        record_property("medharness.id", tc_id)
    if links:
        record_property("medharness.links", ",".join(links))
```

### TypeScript / Vitest / Playwright

Use custom JUnit reporters that emit `<properties>` blocks for `medharness.links`.
Reference implementations are available in the [WebTPS](https://github.com/itercharles/WebTPS) repo.

### Running the gate locally

```bash
# From product repo root, with DHF checked out at ../dhf-repo/
pytest tests/ -q --junitxml=test-results/results.xml
medharness --dhf ../dhf-repo/DHF ci test-coverage --junit-dir test-results
```

Expect output like:

```
[test-coverage] SRS: 12/14 covered
      ↳ uncovered: SRS-012
      ↳ uncovered: SRS-008
```

The command exits non-zero when gaps exist, blocking CI.

---

## CLI Reference

### Scaffold

```bash
medharness init                     # interactive project setup
```

### DHF operations (run from DHF repo or with `--dhf`)

```bash
medharness --dhf DHF dhf item list --type SYS
medharness --dhf DHF dhf item get SYS-001
medharness --dhf DHF dhf item create --type SYS --data '{"title": "My req"}'
medharness --dhf DHF dhf item update SYS-001 --data '{"title": "Updated"}'
medharness --dhf DHF dhf item delete SYS-001
medharness --dhf DHF dhf item transitions CR-001
medharness --dhf DHF dhf item transition CR-001 approved --by "Alice"
medharness --dhf DHF dhf validate schema
medharness --dhf DHF dhf validate traceability
medharness --dhf DHF dhf doc list
medharness --dhf DHF dhf doc generate SYS
medharness --dhf DHF dhf doc export SYS          # PDF output (requires `[docs]`)
medharness --dhf DHF dhf test list
medharness --dhf DHF dhf config doc-types
```

### CI gates (run from product repo)

```bash
medharness ci dhf-validate --dhf DHF
medharness ci test-coverage --dhf DHF --junit-dir test-results
medharness ci evidence bundle --dhf DHF --out-dir dhf-artifacts
medharness ci artifacts generate --dhf DHF --out-dir .
```

### CR workflow commands

```bash
medharness cr workflow intake-github-issue-ci      # CR intake from issue
medharness cr workflow complete-from-github-pr     # CR completion on PR merge
```

### Agent session helpers

```bash
medharness ci claude-session put <pr_number> <session_id>
medharness ci claude-session get <pr_number>
```

---

## Python API

Use `DHFClient` for high-level operations (recommended for product repo automation):

```python
from medharness.client import DHFClient

client = DHFClient(Path("../my-project-DHF/DHF"))

cr   = client.get_item("CR-034")
spec = client.get_cr_context("CR-034")   # {"cr": {...}, "spec": "..."}
client.transition_item("CR-034", "in_review", performed_by="alice")
```

Or use `dhfkit` standalone (no dependency on `medharness`):

```python
from dhfkit.local_adapter import LocalDHFAdapter

adapter = LocalDHFAdapter(Path("DHF"))
items  = adapter.list_items("SRS")
```

---

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `medharness/` | CLI harness, CI gates, CR workflows, `init` scaffolding |
| `dhfkit/` | DHF engine: items, lifecycle, traceability, document generation |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, 12 sample items |
| `docs/` | Architecture, ADRs, compatibility contracts, roadmap |

`dhfkit` has no dependency on `medharness` — the engine can be used standalone.

---

## Docs

- [docs/architecture.md](docs/architecture.md) — packages, scaffold model, DHF lifecycle
- [docs/compatibility-contracts.md](docs/compatibility-contracts.md) — stable public contracts
- [docs/adr/](docs/adr/) — architecture decision records
- [CHANGELOG.md](CHANGELOG.md) — version history

---

## License

MIT — see [LICENSE](LICENSE).
