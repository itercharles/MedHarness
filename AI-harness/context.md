# CompliantFlow — Project Context

CompliantFlow is the AI-first development framework for medical device software. It provides a compliance CI gate, a DHF template, and an AI coding harness — all set up in one command via `compliantflow init`. It is built using the same framework it delivers: IEC 62304 lifecycle, a live DHF in a separate repository, and a four-phase compliance gate on every PR.

---

## Two-Repo Structure

| Repo | Purpose |
|------|---------|
| This repo (`CompliantFlow`) | CLI source code, tests, CI |
| [`compliantflow-dhf`](https://github.com/itercharles/compliantflow-dhf) | Design History File — requirements, risks, traceability, compliance records |

Clone the DHF alongside this repo:

```bash
git clone https://github.com/itercharles/compliantflow-dhf
export PYTHONPATH=.:compliantflow-dhf/DHF
```

---

## Architecture

**Two-CLI split.** `CompliantFlowCore` (`compliantflow/`) is read-only — analysis, traceability, compliance, reporting. DHF mutations (create, update, delete, lifecycle transitions) go through `python -m utils` in compliantflow-dhf. Do not add write operations to `CompliantFlowCore`.

**Graph edge direction.** Edges in `compliantflow/graph.py` run child → parent. `descendants()` means business-upstream (toward requirements). `ancestors()` means business-downstream (toward tests). This is the opposite of the natural reading.

**GitOps approval.** Requirement item types (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit status field change needed. Feature branches mean draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions via `python -m utils item transition`. These are not GitOps-approved.

---

## Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export PYTHONPATH=.:compliantflow-dhf/DHF
.venv/bin/pytest tests/ -q
```

---

## CR Workflow

CR items use two statuses: `planned` (not yet implemented) and `closed` (merged to `main`).

**1. Create the CR**
Confirm the CR is `planned` before writing any code. Create it in compliantflow-dhf:
```bash
cd compliantflow-dhf
PYTHONPATH=.:DHF python -m utils item create --type CR
```

**2. Plan and confirm**
Produce a plan covering:
- Technical design and implementation approach
- DHF impact: which `UC`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `TC`, `RCM` items are affected, need updating, or need to be created
- Test case changes required (new TCs, updated `@links` tags)
- Any compliance implications

Present the plan and wait for explicit approval before writing any code.

**3. Implement**
- Make code changes in the owning layer
- Update or create DHF items as identified in the plan
- Read `tests/fixtures/test_data.py` and relevant doc type configs before writing new tests — field mismatches are the most common source of iteration
- Run tests locally before pushing

**4. Open a PR**
Branch from `main`. Include the CR ID in the PR title — CI Phase 0 requires it.

**5. Monitor to merge**
Watch CI status and fix failures. Merge when all checks pass and the user approves.

**CR closure is automated.** Post-merge CI dispatches `cr-transition.yml` in compliantflow-dhf. Do not manually close CRs.

Do not run compliance checks as a default validation step — they invoke an LLM and are only needed when changing the compliance engine or governance files.

---

## Compliance Gate (CI)

Four-phase gate defined in `.github/workflows/ci-pipeline.yml`:

| Phase | What it checks |
|-------|---------------|
| Phase 0 | CR ID in PR title; CR exists and is `planned` |
| Phase 1 | DHF utils tests pass |
| Phase 2 | SYS API tests pass |
| Phase 3 | CRS API tests pass |
| Phase 4 | Traceability, IEC 62304, IEC 82304-1 compliance |

Post-merge: imports test results into DHF, persists compliance run records, closes CRs, generates evidence reports.

---

## Specialized Agents

Three sub-agents live in `.claude/agent-memory/`:

- **product-manager** — scope, roadmap, business context
- **system-architect** — system design and layer boundaries
- **software-developer** — implementation patterns and conventions
