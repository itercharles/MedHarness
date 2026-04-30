# Contributing to CompliantFlow

CompliantFlow follows a change-request-driven development workflow grounded in
design control. Every non-trivial change starts from a Change Request (CR) in
the DHF repository and passes through structured stages before implementation.

## Development Setup

```bash
git clone https://github.com/compliantflow/compliantflow
cd CompliantFlow
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest tests/ -q
```

Clone the DHF substrate for local compliance checks:

```bash
git clone https://github.com/compliantflow/compliantflow-dhf
pip install dhf_util
```

## Change Workflow

Every non-trivial change passes through three stages, each gated by review:

| Stage | Where | Produced by |
|-------|-------|-------------|
| 1. CR (Change Request) | CompliantFlow-DHF | Contributor |
| 2. Plan Spec | CompliantFlow-DHF | Review + automation |
| 3. Implementation | This repo | Contributor |

### CR Status Model

| Status | Meaning |
|--------|---------|
| `draft` | CR created, not yet submitted |
| `in_review` | CR PR open, awaiting approval |
| `designing` | CR approved; plan spec being generated |
| `implementing` | Plan approved; implementation in progress |
| `completed` | Implementation merged; DHF closed out |
| `cancelled` | CR declined |

## PR Conventions

- Branch naming: `feature/`, `fix/`, `refactor/`
- PR title must include the CR ID: `feat(CR-042): description`
- Body: change summary, DHF files updated, validation run, manual testing remaining

## Before Submitting

```bash
.venv/bin/pytest tests/ -q
.venv/bin/python -m compliantflow --dhf ../compliantflow-dhf/DHF ci test-coverage --junit-dir test-results
```

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
