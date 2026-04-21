# DHF Context

This repository is a **Design History File (DHF)** managed with [CompliantFlow](https://github.com/itercharles/CompliantFlow). It stores all regulatory documentation for this medical device software project as YAML files under version control, verified continuously against IEC 62304, ISO 14971, and related standards in CI.

---

## Environment

```bash
# Install CompliantFlow (downloads latest release)
gh release download --repo itercharles/CompliantFlow \
  --pattern "compliantflow-*.zip" --output compliantflow.zip
unzip compliantflow.zip -d cf
pip install cf/*/compliantflow-*.whl

# DHF utilities (run from this repo's root)
PYTHONPATH=.:DHF python -m utils <command>

# Compliance checks
compliantflow --dhf DHF validate compliance IEC_62304 --governance-dir governance
```

---

## Repository Structure

```
DHF/
  items/           # All DHF items (UC, CRS, SYS, SRS, SWDD, RISK, RCM, CR, ...)
  config/          # Item type schemas and global config
  documents/       # Plans, specifications, release notes
  utils/           # DHF mutation CLI (create, update, lifecycle transitions)
governance/        # Compliance policy files (IEC_62304.yaml, ISO_14971.yaml, ...)
AI-harness/        # AI agent configuration (this folder)
```

---

## Item Types

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
| `CR` | Change Request | Explicit transition (`planned` → `closed`) |
| `REL` | Release | Explicit transition |
| `DEF` | Defect | Explicit transition |
| `TC` | Test Case | GitOps |

---

## Key Invariants

**DHF is read-only via CompliantFlow.** All analysis, traceability, and compliance checking uses the `compliantflow` CLI. DHF mutations (creating items, updating fields, lifecycle transitions) go through `python -m utils`.

**GitOps approval.** Requirement items (`UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `SOUP`, `RISK`, `RCM`) are approved by landing on `main`. No explicit status field — a feature branch means draft or in-review.

**Explicit lifecycle.** `CR`, `REL`, and `DEF` use explicit lifecycle transitions via `python -m utils item transition`. These are not GitOps-approved.

**Graph edge direction.** Traceability edges run child → parent (e.g. SRS `derives_from` SYS). `descendants()` in the graph means upstream toward requirements; `ancestors()` means downstream toward tests.

**Traceability coverage.** Every item must have upstream and downstream links. Orphaned items block the CI gate. Required chain: `UC → CRS → SYS → SRS → SWDD/TC`.

---

## CR Workflow

CR items track all changes to the DHF. Status: `planned` (not yet implemented), `closed` (implemented and merged to main).

**1. Create the CR before writing anything**

```bash
PYTHONPATH=.:DHF python -m utils item create --type CR
```

**2. Make changes**
- Create or update DHF items as needed
- Branch from `main`; include the CR ID in the branch name and PR title

**3. Validate before committing**

```bash
# Schema validity
PYTHONPATH=.:DHF python -m utils validate schema

# Traceability
compliantflow --dhf DHF validate traceability

# Validate a draft item before creating it
compliantflow --dhf DHF validate draft my-item.yaml --type SYS
```

**4. Open PR and merge**
CI validates DHF structure and traceability on every PR. Merge when checks pass.

**5. CR closure**
After merge to `main`, the CR transition workflow runs automatically. If closing manually:

```bash
PYTHONPATH=.:DHF python -m utils item transition CR-XXX closed --by "your name"
```

---

## Common Commands

```bash
# List items by type
PYTHONPATH=.:DHF python -m utils item list --type SYS

# Create a new item
PYTHONPATH=.:DHF python -m utils item create --type SRS \
  --data '{"title": "My requirement", "derives_from": ["SYS-001"]}'

# Update an item field
PYTHONPATH=.:DHF python -m utils item update SRS-001 --data '{"title": "Updated title"}'

# Validate all items against schema
PYTHONPATH=.:DHF python -m utils validate schema

# Check compliance posture
compliantflow --dhf DHF status --governance-dir governance

# Run a compliance check
compliantflow --dhf DHF validate compliance IEC_62304 --governance-dir governance

# Check traceability coverage
compliantflow --dhf DHF validate coverage UC:CRS CRS:SYS SYS:SRS

# Generate compliance report
compliantflow --dhf DHF report compliance IEC_62304 --governance-dir governance
```

---

## User-Configurable Settings

The following are project-specific and set during `compliantflow init`:

| Setting | Location | Description |
|---------|----------|-------------|
| `project_name` | `DHF/config/global.yaml` | Name used in generated documents |
| Selected standards | `governance/` | Only the chosen standards are present |
| Repo name / org | Not stored in DHF | Referenced in CI workflows |
