# AGENTS.md

CompliantFlow is a compliance checking tool for medical device software. It connects to
a project's Design History File (DHF) through a defined interface (CLI or API) and
verifies compliance against IEC 62304, ISO 14971, and IEC 82304-1 in CI. The interface
abstraction means it can integrate with any DHF system, not just the reference
implementation in this repo.

CompliantFlow's own design history file lives in a separate repository,
[compliantflow-dhf](https://github.com/itercharles/compliantflow-dhf).
Clone it alongside this repo and add its `DHF/` directory to `PYTHONPATH`
to enable the CLI and compliance checks.

## Environment

```bash
.venv/                           # virtual environment
PYTHONPATH=.:compliantflow-dhf/DHF  # required for CLI commands and compliance checks
```

## Key Invariants

**Two-CLI split.** `CompliantFlowCore` (`compliantflow/`) is read-only — analysis,
traceability, compliance, reporting. DHF mutations (create, update, delete, lifecycle
transitions) go through `python -m utils`. Do not add write operations to
`CompliantFlowCore`.

**Graph edge direction.** Edges in `compliantflow/graph.py` run child → parent.
`descendants()` means business-upstream (toward requirements). `ancestors()` means
business-downstream (toward tests). This is the opposite of the natural reading.

**GitOps approval.** Requirement item types (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`,
`SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit
status field change needed. Feature branches mean draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions
via `python -m utils item transition`. These are not GitOps-approved.

---

## CR Workflow

CR items use two statuses: `planned` (not yet implemented) and `closed` (merged to `main`).

**1. Create the CR**
Confirm the CR is `planned` before writing any code. Create it with
`python -m utils item create --type CR` if it does not exist.

**2. Plan and confirm**
Analyze the request and produce a plan covering:
- Technical design and implementation approach
- DHF impact: which `UC`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `TC`, `RCM`, and other
  items are affected, need updating, or need to be created
- Test case changes required (new TCs, updated `@links` tags)
- Any compliance implications

Present the plan to the user and wait for explicit approval before writing any code.

**3. Implement**
After approval:
- Make code changes in the owning layer
- Update or create DHF items as identified in the plan
- If the CR involves new tests, read `tests/fixtures/test_data.py` and the relevant
  doc type configs first — field mismatches are the most common source of iteration
- Update test cases and verify `@links` tags are correct
- Run tests locally

**4. Open a PR**
Branch from `main`. Include the CR ID in the PR title — CI Phase 0 requires it.

**5. Monitor to merge**
Stay active after opening the PR — do not treat it as a handoff:
- Watch CI status and fix any failures
- Address review comments with follow-up commits
- Merge when all checks pass and the user approves

**CR closure is automated.** After merge to `main`, the post-merge CI extracts CR IDs
from the merge commit subject and dispatches the `cr-transition.yml` workflow in
compliantflow-dhf, which transitions each CR to `closed` and commits the change back.
Do not manually set CRs to `closed` — the automation handles it. If a CR needs to be
closed after manual verification (outside of a code merge), trigger the workflow
directly from the GitHub Actions UI in the compliantflow-dhf repo.

Do not run compliance checks as a default validation step — they invoke an LLM and
are only needed when changing compliance engine or governance files.

