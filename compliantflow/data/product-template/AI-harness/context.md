# Project Context — {{project_name}}

This is the product repository for **{{project_name}}**, a medical device software project developed under **{{standards}}**.

Compliance is enforced automatically on every PR via CompliantFlow. The Design History File (DHF) lives in a separate repository and tracks all regulatory documentation.

---

## Two-Repo Structure

| Repo | Purpose |
|------|---------|
| This repo | Product source code |
| `{{dhf_repo}}` | Design History File — requirements, risks, traceability, compliance records |

For local compliance checks, clone the DHF repo alongside this one:

```bash
git clone https://github.com/{{dhf_repo}} ../$(basename {{dhf_repo}})
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

## CR Workflow

Every tracked change starts with a Change Request (CR) in the DHF repo.

**Before writing any code:**

```bash
# In the DHF repo
PYTHONPATH=.:DHF python -m utils item create --type CR
# Note the CR ID (e.g. CR-042)
```

**Branch naming and PR title must include the CR ID:**

```
feat/CR-042-add-input-validation
feat(CR-042): add input validation
```

The compliance CI gate (Phase 0) rejects PRs without a CR ID in the title.

---

## Compliance Gate

The CI workflow (`.github/workflows/compliance.yml`) runs on every push and PR:

1. **Traceability check** — no orphaned items, all requirements have upstream and downstream links
2. **Compliance policy checks** — {{standards}} policy rules pass
3. **Coverage check** — UC → CRS → SYS → SRS chain is complete

**Local compliance check:**

```bash
DHF_DIR="../$(basename {{dhf_repo}})/DHF"
GOVERNANCE_DIR="../$(basename {{dhf_repo}})/governance"

compliantflow --dhf "$DHF_DIR" validate traceability
compliantflow --dhf "$DHF_DIR" validate compliance IEC_62304 --governance-dir "$GOVERNANCE_DIR"
compliantflow --dhf "$DHF_DIR" status --governance-dir "$GOVERNANCE_DIR"
```

---

## User-Configurable Settings

| Setting | Description |
|---------|-------------|
| `{{dhf_repo}}` | DHF repository — set during `compliantflow init` |
| Selected standards | `{{standards}}` — determines which policy checks run |
