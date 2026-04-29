# CompliantFlow

**The AI-first development framework for medical device software.**

One command sets up everything: a Design History File, a compliance CI gate, and an AI coding harness — pre-configured for IEC 62304, ISO 14971, and ISO 13485. AI agents generate code and documentation; CompliantFlow ensures every commit meets regulatory requirements before merge.

---

## Why CompliantFlow

| Scenario | Compliance debt | Audit prep |
|---|---|---|
| Traditional (no AI, no tool) | Accumulates every sprint | 4–6 weeks |
| AI coding tools only | Accumulates faster | Same or worse |
| CompliantFlow only | Zero | 1 day |
| **AI coding + CompliantFlow** | **Zero** | **1 day** |

Self-built CI/CD knows code quality. CompliantFlow knows IEC 62304 / ISO 14971 semantics — traceability chains, risk coverage, DHF integrity. It is the trust layer between AI-generated code and regulatory requirements.

---

## Three-Layer Framework

```
┌─────────────────────────────────────────────────────┐
│  AI Layer — AI-harness/                             │
│  Guides AI agents to generate compliant code and    │
│  DHF documents. Claude, Cursor, Copilot supported.  │
├─────────────────────────────────────────────────────┤
│  Validation Layer — CompliantFlow CLI               │
│  CI gate enforcing traceability, compliance policy, │
│  and coverage on every PR. Exits 1 on failure.      │
├─────────────────────────────────────────────────────┤
│  Infrastructure Layer — compliantflow init          │
│  One command sets up both repos with everything     │
│  above pre-configured and ready to push.            │
└─────────────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Install

```bash
gh release download --repo itercharles/CompliantFlow \
  --pattern "compliantflow-*.zip" --output compliantflow.zip
unzip compliantflow.zip -d cf
pip install cf/*/compliantflow-*.whl
```

### 2. Run `compliantflow init`

```bash
compliantflow init
```

`init` prompts for your project details and writes locally — no GitHub operations. It creates:

| What | Where |
|---|---|
| DHF template (items, governance, utils, CI) | Your DHF local directory |
| AI harness (context, checklists, adapters) | Your product repo directory |
| Compliance CI gate workflow | `product-repo/.github/workflows/compliance.yml` |

### 3. Push and open a PR

Follow the printed git commands. Add the required secrets (`COMPLIANTFLOW_TOKEN`, `DHF_REPO_TOKEN`) and merge. From that point, every PR is compliance-checked automatically.

Full walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## AI Harness

Both repos ship with `AI-harness/` pre-configured for your project:

- **`context.md`** — model-agnostic project context (DHF structure, item types, when to update the DHF, compliance gate semantics)
- **`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`** — entry points for Claude Code, generic agents, Gemini CLI
- **`pre-checklist.md` / `post-checklist.md`** — task workflow checklists
- **`adapters/.cursorrules`** — copy to repo root for Cursor
- **`adapters/copilot-instructions.md`** — copy to `.github/` for GitHub Copilot

Open either repo in your AI coding tool and it immediately understands the DHF structure, CR workflow, and compliance requirements.

---

## Compliance Gate

The CI workflow runs four checks on every push and PR:

1. **CR linkage** — PR title must reference a planned Change Request
2. **Traceability** — no orphaned items; every requirement has upstream and downstream links
3. **Compliance policy** — IEC 62304, ISO 14971, ISO 13485 policy checks pass
4. **Coverage** — UC → CRS → SYS → SRS chain is complete

```bash
# Run locally before pushing
compliantflow --dhf DHF ci gate acceptance
compliantflow --dhf DHF validate traceability
compliantflow --dhf DHF validate compliance IEC_62304 --governance-dir governance
compliantflow --dhf DHF status --governance-dir governance
```

---

## Command Reference

```
compliantflow [--dhf PATH] COMMAND

Setup:
  init                            Interactive infrastructure onboarding

Compliance:
  ci gate acceptance              Run the CI-facing DHF acceptance gate
  ci run acceptance               High-level acceptance orchestration for product CI
  ci evidence import PATH...      Import CI JUnit evidence into the DHF
  ci artifacts generate           Generate CI-ready DHF PDF artifacts
  ci run artifacts                High-level artifact orchestration for product CI
  validate traceability           Check all items have upstream/downstream links
  validate compliance STANDARD    Run policy checks (IEC_62304, ISO_14971, ...)
  validate coverage PARENT:CHILD  Check coverage between item types
  validate release REL-ID         Evaluate release readiness
  validate draft FILE             Validate a draft item before creating it
  status                          At-a-glance compliance posture summary

Reports:
  report compliance STANDARD      Generate compliance report (PDF or JSON)
  report traceability TYPES...    Build traceability matrix PDF
  export submission               Assemble 510(k) submission evidence ZIP

Change management:
  cr check-status CR-ID           Check CR implementation status
  cr generate-report CR-ID        Generate CR evidence report

Tests:
  test import PATH                Import JUnit XML results
  test list                       List all test results
  test status TC-ID               Check a single test case

AI tools:
  context                         Generate agent context package
  review-pr                       Compliance-aware PR review checklist

DHF automation facade:
  dhf item list|get|create|update|delete
  dhf item transition             Execute a lifecycle transition through adapter
  dhf context implementation      Write an approved CR implementation package

Migration:
  migrate rdm SOURCE_DIR          Migrate from Innolitics RDM
```

---

## DHF Automation

CompliantFlow exposes a generic DHF automation facade for product CI and agent
workflows. The facade delegates to the configured DHF adapter/provider so product
repositories do not need to know DHF storage paths.

```bash
compliantflow --dhf DHF dhf item list --type SYS
compliantflow --dhf DHF dhf item create --type SRS \
  --data '{"title": "My requirement", "derives_from": ["SYS-001"]}'
compliantflow --dhf DHF dhf item transition CR-001 closed --by "Alice"
compliantflow --dhf DHF dhf context implementation --cr CR-001 --out-dir /tmp/dhf-context
```

CI pipelines should use the stable `ci` namespace for gate/evidence/artifact
workflows:

```bash
compliantflow --dhf DHF ci run acceptance \
  --junit-dir test-results/srs \
  --junit-dir test-results/sys
compliantflow --dhf DHF ci gate acceptance --junit test-results.xml
compliantflow --dhf DHF ci evidence import test-results.xml --run-id "$GITHUB_RUN_ID"
compliantflow --dhf DHF ci run artifacts --out-dir artifacts/dhf \
  --junit-dir test-results/srs \
  --junit-dir test-results/sys
compliantflow --dhf DHF ci artifacts generate --out-dir artifacts/dhf --junit test-results.xml
```

The DHF repository still owns the local YAML/Git provider and schema/document
tooling. Direct DHF utils commands remain available for DHF maintainers:

```bash
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item create --type SRS \
  --data '{"title": "My requirement", "derives_from": ["SYS-001"]}'
PYTHONPATH=.:DHF python -m utils item transition CR-001 closed --by "Alice"
PYTHONPATH=.:DHF python -m utils validate schema
```

---

## 510(k) Submission Package

```bash
compliantflow --dhf DHF export submission \
  --governance-dir governance \
  --output-dir ./submission
```

Produces `submission_YYYY-MM-DD.zip` with traceability report, compliance reports, SOUP list, risk summary, test results, and CR evidence — mapped to FDA eSTAR sections.

---

## For CompliantFlow Contributors

See [AGENTS.md](AGENTS.md) for the development workflow, CR process, and architecture.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
git clone https://github.com/itercharles/compliantflow-dhf
export PYTHONPATH=.:compliantflow-dhf/DHF
.venv/bin/pytest tests/ -q
```
