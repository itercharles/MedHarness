# AGENTS.md

This repository is a **Design History File (DHF)** managed with [CompliantFlow](https://github.com/itercharles/CompliantFlow). It stores all regulatory documentation for this medical device software project as YAML files under version control, verified continuously against IEC 62304, ISO 14971, and IEC 82304-1 in CI.

## Environment

```bash
# Install CompliantFlow
pip install compliantflow

# DHF utilities (run from this repo's root)
PYTHONPATH=.:DHF python -m utils <command>

# Compliance checks
compliantflow --dhf DHF validate compliance IEC_62304 --governance-dir governance
```

## Repository Structure

```
DHF/
  items/          # All DHF items (UC, CRS, SYS, SRS, SWDD, RISK, RCM, CR, ...)
  config/         # Item type schemas and global lifecycle config
  documents/      # Plans, specifications, release notes
  governance/     # Compliance policy files (IEC_62304.yaml, ISO_14971.yaml, ...)
  utils/          # DHF mutation CLI (create, update, lifecycle transitions)
  test-results/   # Test result records (written by CI)
  compliance-runs/ # Compliance run history (written by CI)
```

## Key Invariants

**DHF is read-only via CompliantFlow.** All analysis, traceability, and compliance checking uses the `compliantflow` CLI. DHF mutations (creating items, updating fields, lifecycle transitions) go through `python -m utils`.

**GitOps approval.** Requirement items (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit status field — a feature branch means draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions via `python -m utils item transition`. These are not GitOps-approved.

**Graph edge direction.** Traceability edges run child → parent (e.g. SRS derives_from SYS). `descendants()` in the graph means upstream toward requirements.

## CR Workflow

CR items track changes to the DHF. Use status `planned` (not yet implemented) and `closed` (implemented and merged).

**1. Create the CR**

```bash
PYTHONPATH=.:DHF python -m utils item create --type CR
```

**2. Make changes**
- Create or update DHF items as needed
- Branch from `main`; include the CR ID in the commit/PR title

**3. Validate before committing**

```bash
# Check schema validity
PYTHONPATH=.:DHF python -m utils validate schema

# Preview traceability
compliantflow --dhf DHF validate traceability

# Check a draft item before creating it
compliantflow --dhf DHF validate draft my-item.yaml --type SYS
```

**4. Open PR and merge**
CI validates DHF structure and traceability on every PR. Merge when checks pass.

**5. CR closure**
After merge to `main`, manually transition the CR to `closed`:

```bash
PYTHONPATH=.:DHF python -m utils item transition CR-XXX closed --by "your name"
```

## Common Commands

```bash
# List items by type
PYTHONPATH=.:DHF python -m utils item list --type SYS

# Create a new item
PYTHONPATH=.:DHF python -m utils item create --type SRS --data '{"title": "My req", "derives_from": ["SYS-001"]}'

# Validate all items against schema
PYTHONPATH=.:DHF python -m utils validate schema

# Check compliance posture
compliantflow --dhf DHF status --governance-dir governance

# Run a compliance check
compliantflow --dhf DHF validate compliance IEC_62304 --governance-dir governance

# Check traceability coverage
compliantflow --dhf DHF validate coverage UC:CRS CRS:SYS SYS:SRS
```
