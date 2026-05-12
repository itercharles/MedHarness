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

`medharness init` is zero-prompt — it scaffolds a single-repo project in the
current directory. The project name is derived from the directory name.

```bash
mkdir my-medical-device && cd my-medical-device
python -m venv .venv && source .venv/bin/activate
pip install medharness
medharness init
```

After `init` completes, here's what exists on disk:

```
my-medical-device/                  # single repo — DHF + source together
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
│   ├── documents/
│   │   ├── specs/                  # Jinja2 spec templates (.j2)
│   │   └── plans/                  # development_plan.md, verification_plan.md, …
│   └── README.md
├── .github/
│   └── prompts/                    # optional prompt files for repo-local automation
├── tests/                          # product test suite
├── CLAUDE.md                       # agent entrypoint
├── .gitignore
└── README.md                       # project README
```

The scaffolded items are **starter samples** — replace them with your project's
real requirements, architecture, and plans before using this for a regulated product.

**Initialize git and push:**

```bash
git init && git add -A
git commit -m "feat: initialize My Medical Device with MedHarness"
git remote add origin https://github.com/<org>/my-medical-device
git push -u origin main
```

---

## Automation Model

MedHarness no longer ships prescribed GitHub workflow files as part of the
product surface. The stable interface is the CLI.

Use the CLI directly from whichever automation layer you prefer:
- GitHub Actions
- GitLab CI
- Jenkins
- local scripts
- internal orchestration systems

Typical entrypoints are:

```bash
medharness ci dhf-validate --dhf DHF
medharness ci test-coverage --dhf DHF --junit-dir test-results
medharness --dhf DHF ci analyze-cr --cr CR-034
medharness --dhf DHF ci design-cr --cr CR-034
medharness --dhf DHF ci develop-cr --cr CR-034
medharness --dhf DHF ci validate-design --cr CR-034
medharness --dhf DHF ci validate-code --cr CR-034
medharness --dhf DHF ci validate-branch --cr CR-034
medharness ci cr-status --cr CR-034 --stage spec --pr 18
medharness --dhf DHF ci evidence bundle --out-dir artifacts --junit-dir test-results
medharness ci github-event --event "$GITHUB_EVENT_PATH"
```

## How a Change Request flows

Every non-trivial change starts as a **Change Request (CR)** in the DHF.
CRs move through AI-assisted stages, each gated by human approval. How those
stages are wired into automation is up to the client repo:

```
Issue → CR review → analyze-cr → design-cr → develop-cr → cr-complete
```

| Stage | Trigger | What MedHarness does |
|-------|---------|---------------------|
| **CR intake** | Issue milestoned | Creates CR item in DHF, opens draft PR (`cr workflow intake-github-issue-ci`) |
| **analyze-cr** | CR PR approved | Runs Claude to write a spec, self-corrects against schema, commits to `docs/cr-specs/` (`ci analyze-cr`) |
| **design-cr** | Spec PR approved | Runs Claude to create/update DHF items, validates schema + traceability (`ci design-cr`) |
| **develop-cr** | Design PR approved | Runs Claude to implement code, opens implementation PR (`ci develop-cr`) |
| **cr-complete** | PR merged | Transitions CR to `completed` in the DHF (`cr workflow complete-from-github-pr`) |

When a PR receives review feedback, re-run the same command with `--pr N` to
revise the existing output based on reviewer comments.

To let external automation decide whether a CR stage is ready to advance,
use the CLI's machine-readable status surface rather than embedding policy in
workflow YAML:

```bash
medharness ci cr-status --cr CR-034 --branch spec/CR-034 --pr 18
```

To catch deterministic issues before a PR is opened, client automation can run
the same preflight validators directly:

```bash
medharness --dhf DHF ci validate-design --cr CR-034
medharness --dhf DHF ci validate-code --cr CR-034 --since-ref origin/main
medharness --dhf DHF ci validate-branch --cr CR-034 --since-ref origin/main
```

`validate-branch` requires the approved spec file to exist for the CR, but it
does not require a fresh diff to that spec on the implementation branch. That
matches the normal flow where a `feat/CR-*` branch is cut after the spec has
already been merged.

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
# From project root
pytest tests/ -q --junitxml=test-results/results.xml
medharness --dhf DHF ci test-coverage --junit-dir test-results
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
medharness init                     # zero-prompt single-repo project setup
```

### DHF operations (run with `--dhf DHF`)

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

### CI gates

```bash
medharness ci dhf-validate --dhf DHF
medharness ci test-coverage --dhf DHF --junit-dir test-results
medharness ci evidence bundle --dhf DHF --out-dir artifacts
```

### CR generation commands

Encapsulate the full AI loop for each CR stage: prompt assembly (with embedded
DHF impact skills) → `claude -p` invocation → validate → self-correct.

```bash
# Initial generation
medharness --dhf DHF ci analyze-cr --cr CR-034   # write docs/cr-specs/CR-034-Spec.md
medharness --dhf DHF ci design-cr  --cr CR-034   # create/update DHF items
medharness --dhf DHF ci develop-cr --cr CR-034   # implement code

# Revision based on PR review feedback
medharness --dhf DHF ci analyze-cr --cr CR-034 --pr 42
medharness --dhf DHF ci design-cr  --cr CR-034 --pr 42
medharness --dhf DHF ci develop-cr --cr CR-034 --pr 42
```

`ANTHROPIC_MODEL` env var selects the Claude model. `GH_TOKEN` is required when
`--pr` is used (fetches review comments from the GitHub API).

Each command outputs JSON to stdout:

```json
{ "cr_id": "CR-034", "stage": "spec", "status": "ok",
  "corrections": 0, "validation": "passed", "errors": [],
  "spec_path": "docs/cr-specs/CR-034-Spec.md",
  "spec_json_path": "docs/cr-specs/CR-034-Spec.json",
  "started_at": "2026-05-11T14:23:45+00:00", "elapsed_ms": 28500 }
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

client = DHFClient(Path("DHF"))

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
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, sample items |
| `tests/` | MedHarness and dhfkit test suites |
| `docs/` | Architecture, ADRs, compatibility contracts |

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
