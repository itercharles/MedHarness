# CompliantFlow — Project Context

CompliantFlow is the AI-first development framework for medical device software. It provides a compliance CI gate, a DHF template, and an AI coding harness — all set up in one command via `compliantflow init`. It is built using the same framework it delivers: IEC 62304 lifecycle, a live DHF in a separate repository, and a four-phase compliance gate on every PR.

---

## Two-Repo Structure

| Repo | Purpose |
|------|---------|
| This repo (`CompliantFlow`) | CLI source code, tests, CI |
| [`compliantflow-dhf`](https://github.com/itercharles/compliantflow-dhf) | Design History File — requirements, risks, traceability, compliance records |

For local compliance checks, clone the DHF repo alongside this one:

```bash
git clone https://github.com/itercharles/compliantflow-dhf
export PYTHONPATH=.:compliantflow-dhf/DHF
```

---

## When a Code Change Requires a DHF Update

A code change **requires** a DHF update when it:

| Change type | DHF action needed |
|-------------|-------------------|
| Adds or modifies a user-facing behaviour | Create or update a UC or CRS item |
| Adds or modifies system or software behaviour | Create or update a SYS or SRS item |
| Introduces a new risk or mitigates an existing one | Create or update a RISK or RCM item |
| Changes the software architecture | Update SYSARCH item |
| Changes a third-party library (SOUP) | Create or update a SOUP item |
| Adds or modifies a test | Create or update a TC item with correct `@links` tags |

A code change does **not** require a DHF update for: refactoring with no behaviour change, dependency version bumps with no API change, CI/build changes.

---

## DHF Item Types

All regulatory documentation lives in `compliantflow-dhf/DHF/items/`. Item types:

| Type | Description | Approval |
|------|-------------|----------|
| `UC` | Use Case | GitOps (land on main) |
| `CRS` | Customer Requirement | GitOps |
| `SYS` | System Requirement | GitOps |
| `SRS` | Software Requirement | GitOps |
| `SWDD` | Software Detailed Design | GitOps |
| `SYSARCH` | System Architecture | GitOps |
| `RISK` | Risk item | GitOps |
| `RCM` | Risk Control Measure | GitOps |
| `SOUP` | Software of Unknown Provenance | GitOps |
| `TC` | Test Case | GitOps |
| `CR` | Change Request | Explicit transition (`planned` → `closed`) |
| `REL` | Release | Explicit transition |
| `DEF` | Defect | Explicit transition |

**GitOps approval:** items are approved by landing on `main`. A feature branch means draft or in-review — no explicit status field needed.

**Traceability chain:** `UC → CRS → SYS → SRS → SWDD / TC`. Every item must have upstream and downstream links. Orphaned items block the CI gate.

**Graph edge direction:** edges run child → parent (e.g. SRS `derives_from` SYS). This is the canonical direction.

---

## DHF Commands

Run these from the DHF repo root (cloned alongside this repo at `compliantflow-dhf/`):

```bash
cd compliantflow-dhf

# Create a new item
PYTHONPATH=.:DHF python -m utils item create --type SRS \
  --data '{"title": "My requirement", "derives_from": ["SYS-001"]}'

# Update an item field
PYTHONPATH=.:DHF python -m utils item update SRS-001 --data '{"title": "Updated title"}'

# List items by type
PYTHONPATH=.:DHF python -m utils item list --type SYS

# Validate schema
PYTHONPATH=.:DHF python -m utils validate schema

# Lifecycle transition (CR, REL, DEF only)
PYTHONPATH=.:DHF python -m utils item transition CR-042 closed --by "your name"
```

---

## CR Workflow

CR items use two statuses: `planned` (not yet implemented) and `closed` (merged to `main`).

**Before writing any code:**

```bash
cd compliantflow-dhf
PYTHONPATH=.:DHF python -m utils item create --type CR
# Note the CR ID (e.g. CR-042)
```

**Branch naming and PR title must include the CR ID:**

```
feat/CR-042-description
feat(CR-042): description
```

The compliance CI gate (Phase 0) rejects PRs without a CR ID in the title.

---

## Compliance Gate

The CI workflow (`.github/workflows/ci-pipeline.yml`) runs on every PR:

1. **Traceability check** — no orphaned items, all requirements have upstream and downstream links
2. **Compliance policy checks** — IEC 62304, ISO 14971 policy rules pass
3. **Coverage check** — UC → CRS → SYS → SRS chain is complete

**Local compliance check:**

```bash
DHF_DIR="compliantflow-dhf/DHF"
GOVERNANCE_DIR="compliantflow-dhf/governance"

compliantflow --dhf "$DHF_DIR" validate traceability
compliantflow --dhf "$DHF_DIR" validate compliance IEC_62304 --governance-dir "$GOVERNANCE_DIR"
compliantflow --dhf "$DHF_DIR" status --governance-dir "$GOVERNANCE_DIR"
```

---

## Architecture

**Two-CLI split.** `CompliantFlowCore` (`compliantflow/`) is read-only — analysis, traceability, compliance, reporting. DHF mutations go through `python -m utils` in compliantflow-dhf. Do not add write operations to `CompliantFlowCore`.

**Graph edge direction.** Edges in `compliantflow/graph.py` run child → parent. `descendants()` means business-upstream (toward requirements). `ancestors()` means business-downstream (toward tests). This is the opposite of the natural reading.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions via `python -m utils item transition`. These are not GitOps-approved.

**Environment:**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export PYTHONPATH=.:compliantflow-dhf/DHF
.venv/bin/pytest tests/ -q
```

**CI phases** (`ci-pipeline.yml`):

| Phase | What it checks |
|-------|---------------|
| Phase 0 | CR ID in PR title; CR exists and is `planned` |
| Phase 1 | DHF utils tests pass |
| Phase 2 | SYS API tests pass |
| Phase 3 | CRS API tests pass |
| Phase 4 | Traceability, IEC 62304, IEC 82304-1 compliance |

Post-merge: imports test results into DHF, persists compliance run records, closes CRs, generates evidence reports.

**Development workflow notes:**

- Before writing code: produce a plan covering DHF impact (which `UC`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `TC`, `RCM` items are affected), test case changes, compliance implications. Wait for user approval before implementing.
- Read `tests/fixtures/test_data.py` and relevant doc type configs before writing new tests — field mismatches are the most common source of iteration.
- CR closure is automated: post-merge CI dispatches `cr-transition.yml` in compliantflow-dhf. Do not manually close CRs.
- Do not run compliance checks as a default validation step — they invoke an LLM and are only needed when changing the compliance engine or governance files.

**Specialized agents** (`.claude/agent-memory/`):

- **product-manager** — scope, roadmap, business context
- **system-architect** — system design and layer boundaries
- **software-developer** — implementation patterns and conventions
