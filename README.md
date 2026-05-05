# MedHarness

**AI harness and DHF tooling for medical device software teams.**

MedHarness is an open-source framework for building AI-driven engineering workflows on IEC 62304 /
FDA-regulated software projects. It combines two things:

1. **`medharness`** — a CI harness that structures how AI agents (Claude Code) interact with a
   Design History File: pre-computing context, enforcing approval gates, persisting decisions,
   and generating audit-ready evidence.

2. **`dhfkit`** — a standalone DHF engine for managing items, enforcing traceability
   (UC → CRS → SRS → SWDD → TC), validating schema, and generating specification documents.

[![PyPI](https://img.shields.io/pypi/v/medharness)](https://pypi.org/project/medharness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

> **Harness engineering:** Rather than prompting an AI to "do compliance," MedHarness
> pre-computes the DHF context, injects it into the agent environment, defines approval gates
> the agent must pass through, and captures the agent's decisions back into the DHF — so the
> engineer controls the loop, not the agent.

---

## Install

```bash
pip install medharness[full]
```

`[full]` includes the `ai` (Gemini-based AI review) and `docs` (PDF export) extras.
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
```

---

## Quick Start

```bash
medharness init
```

Interactively scaffolds two repos:

- **DHF repo** — `DHF/config/`, item YAML templates, spec/plan Jinja2 templates,
  GitHub Actions workflows for CR analysis, design, and CI validation
- **Product repo files** — `CLAUDE.md`, `engineering-control.yml`, `cr-complete.yml`,
  Claude Code skills (`.claude/skills/`)

---

## How it works

A Change Request flows through five AI-assisted stages, each enforced by GitHub Actions:

```
Issue → cr-analyze (AI spec) → cr-design (AI DHF items) → cr-develop (AI code) → cr-complete
```

At each stage MedHarness:
- **Pre-computes DHF context** (`medharness dhf context overview`) and injects it as `$DHF_CONTEXT`
- **Runs Claude** with `--dangerously-skip-permissions` inside the DHF repo
- **Commits transitions** back to the DHF (`medharness dhf item transition --commit --push`)
- **Stores session IDs** in PR comments for iterative review (`medharness ci claude-session put/get`)

---

## CLI surface

```
medharness init

# DHF operations (run from DHF repo with --dhf DHF)
medharness --dhf DHF dhf item list|get|create|update|delete|transitions|transition
medharness --dhf DHF dhf validate schema|traceability
medharness --dhf DHF dhf doc list|generate|export
medharness --dhf DHF dhf test list
medharness --dhf DHF dhf context overview|implementation
medharness --dhf DHF dhf config doc-types

# CI gates (run from product repo)
medharness ci dhf-validate --dhf DHF
medharness ci test-coverage --dhf DHF
medharness ci evidence bundle --dhf DHF --out-dir ...
medharness ci artifacts generate --dhf DHF --out-dir ...

# GitHub Actions helpers
medharness ci github-event --github-output "$GITHUB_OUTPUT"
medharness ci claude-session put <pr_number> <session_id>
medharness ci claude-session get <pr_number>

# CR workflow
medharness cr workflow intake-github-issue-ci
medharness cr workflow complete-from-github-pr
```

---

## Python API

Use `dhfkit` directly in product repo automation without shelling out:

```python
from medharness.client import DHFClient

client = DHFClient(Path("../my-project-DHF/DHF"))
cr = client.get_item("CR-034")
context = client.get_cr_context("CR-034")   # {"cr": {...}, "spec": "..."}
client.transition_item("CR-034", "in_review", performed_by="alice")
```

Or use `dhfkit` standalone (no dependency on `medharness`):

```python
from dhfkit.local_adapter import LocalDHFAdapter

adapter = LocalDHFAdapter(Path("DHF"))
items = adapter.list_items("SRS")
```

---

## Repository layout

| Directory | Purpose |
|-----------|---------|
| `medharness/` | CLI harness, CI gates, CR workflows, `init` scaffolding |
| `dhfkit/` | DHF engine: items, lifecycle, traceability, document generation |
| `dhfkit/templates/` | Starter DHF scaffold — config, specs, plans, sample items |
| `docs/` | Architecture, ADRs, compatibility contracts, roadmap |

`dhfkit` has no dependency on `medharness` and can be used standalone.

---

## Docs

- [docs/roadmap.md](docs/roadmap.md) — vision and milestone plan
- [docs/architecture.md](docs/architecture.md) — packages, scaffold model, DHF lifecycle
- [docs/compatibility-contracts.md](docs/compatibility-contracts.md) — stable public contracts
- [docs/adr/](docs/adr/) — architecture decision records
- [CHANGELOG.md](CHANGELOG.md) — version history

---

## License

MIT — see [LICENSE](LICENSE).
