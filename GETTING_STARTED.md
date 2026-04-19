# Getting Started with CompliantFlow v2.0.6

CompliantFlow is a **CI compliance gate** for medical device software projects.
It connects to your Design History File (DHF) and blocks merges that would
violate IEC 62304, ISO 14971, or ISO 13485 — before they land in your main branch.

---

## Prerequisites

- Python 3.11 or later
- [GitHub CLI](https://cli.github.com) (`gh`) installed and authenticated
- A product code repository on GitHub

---

## Step 1 — Install

You will receive a `COMPLIANTFLOW_TOKEN` (GitHub PAT with `contents: read` access to
the CompliantFlow release repository). Authenticate once:

```bash
gh auth login
```

Then download and install:

```bash
gh release download v2.0.6 --repo itercharles/CompliantFlow \
  --pattern "compliantflow-*.zip" \
  --output compliantflow.zip
unzip compliantflow.zip -d cf
pip install cf/*/build/compliantflow-*.whl
```

Verify:

```bash
compliantflow --help
```

---

## Step 2 — Run `compliantflow init`

This single command sets up the full infrastructure for your project interactively:

```bash
compliantflow init
```

You will be prompted for:

| Prompt | Example |
|--------|---------|
| GitHub org or username | `acme-medical` |
| Product repository name | `insulin-pump` |
| Project name (for documents) | `Insulin Pump Firmware` |
| Create a DHF repository? | `Y` |
| DHF repository name | `insulin-pump-dhf` |
| Applicable standards | IEC 62304, ISO 14971 |
| Enable AI compliance checks? | `Y` |
| LLM provider | `gemini` |
| Gemini API key | `****` |

After you confirm, `init` will:

1. Create a private DHF repository pre-configured with your project name and selected standards
2. Open a pull request in your product repo adding `.github/workflows/compliance.yml`
3. Set `GEMINI_API_KEY` (or `COMPLIANTFLOW_OLLAMA_URL`) in your product repo secrets

**After `init` completes, two manual steps remain:**

```
1. Add COMPLIANTFLOW_TOKEN to your product repo secrets
   (provided by your account representative)

2. Create a fine-grained PAT with "Contents: Read" on your DHF repo,
   add it as DHF_REPO_TOKEN to your product repo secrets

3. Review and merge the compliance PR opened by init
```

---

## Step 3 — Merge the compliance PR

The PR opened by `init` adds the compliance gate workflow. Once the two secrets
above are in place, merge the PR. From that point on, every push and PR in your
product repo is checked against:

- Traceability links (no orphaned requirements)
- IEC 62304 / ISO 14971 policy compliance
- Coverage between item types (UC → CRS → SYS → SRS)

The gate **blocks merges** on any failure.

---

## Step 4 — Add a CI install step (for your product repo's CI)

If your product repo has other CI workflows that also need to call `compliantflow`,
add this install step to them:

```yaml
- name: Install CompliantFlow
  env:
    GH_TOKEN: ${{ secrets.COMPLIANTFLOW_TOKEN }}
  run: |
    gh release download v2.0.6 --repo itercharles/CompliantFlow \
      --pattern "compliantflow-*.zip" \
      --output compliantflow.zip
    unzip compliantflow.zip -d cf
    pip install cf/*/build/compliantflow-*.whl
```

---

## Step 5 — Maintain your DHF

Open your DHF repository in Claude Code to create and update items with AI assistance:

```bash
gh repo clone YOUR_ORG/YOUR_PRODUCT-dhf
cd YOUR_PRODUCT-dhf
claude
```

The DHF includes `CLAUDE.md` and `AGENTS.md` so the AI agent understands DHF item
types, lifecycle rules, and compliance requirements.

To manage items manually:

```bash
# Install DHF utils dependencies (from the DHF repo root)
pip install click jinja2 markdown pydantic PyYAML gitpython

# Create a System Requirement
PYTHONPATH=.:DHF python -m utils item create --type SYS \
  --data '{"title": "System shall validate all inputs", "category": "Functional"}'

# List all items
PYTHONPATH=.:DHF python -m utils item list

# Validate DHF schema
PYTHONPATH=.:DHF python -m utils validate schema
```

---

## Step 6 — Run compliance checks locally

Before pushing, run checks locally to catch failures early:

```bash
# Traceability
compliantflow --dhf DHF validate traceability

# IEC 62304 compliance
compliantflow --dhf DHF validate compliance IEC_62304 \
  --governance-dir governance

# At-a-glance posture
compliantflow --dhf DHF status --governance-dir governance
```

---

## Step 7 — 510(k) Submission Package

When preparing a regulatory submission:

```bash
compliantflow --dhf DHF export submission \
  --governance-dir governance \
  --output-dir ./submission
```

This produces `submission_YYYY-MM-DD.zip` with all required evidence artifacts
mapped to FDA eSTAR submission sections. The command fails if any compliance check
is failing — fix all gate failures first, or use `--force` to override.

---

## Command Reference

```
compliantflow [--dhf PATH] COMMAND

Setup:
  init                            Interactive infrastructure onboarding

Compliance:
  validate traceability           Check all items have upstream/downstream links
  validate compliance STANDARD    Run policy checks (e.g. IEC_62304, ISO_14971)
  validate coverage PARENT:CHILD  Check coverage between item types (e.g. UC:CRS)
  validate release REL-ID         Evaluate release readiness
  validate draft FILE             Validate a draft item before creating it
  status                          At-a-glance compliance posture summary

Reports:
  report compliance STANDARD      Generate compliance PDF report
  traceability matrix TYPES...    Build traceability matrix PDF
  export submission               Assemble 510(k) submission evidence ZIP

Change management:
  cr check-status CR-ID           Check CR implementation status
  cr generate-report CR-ID        Generate CR evidence report (git history)

Tests:
  test import PATH                Import JUnit XML results into DHF
  test list                       List all test results
  test status TC-ID               Check a single test case

AI tools:
  context                         Generate agent context package
  review-pr                       Compliance-aware PR review checklist

Migration:
  migrate rdm SOURCE_DIR          Migrate from Innolitics RDM
```

---

## Governance Files

The `governance/` directory in your DHF contains compliance policy files:

| File | Standard | Scope |
|---|---|---|
| `IEC_62304.yaml` | IEC 62304:2006+AMD1:2015 | Medical device software lifecycle |
| `ISO_14971.yaml` | ISO 14971:2019 | Risk management |
| `IEC_82304_1.yaml` | IEC 82304-1:2016 | Health software |
| `ISO_13485.yaml` | ISO 13485:2016 | Quality management systems |

`compliantflow init` includes only the standards you select.

---

## Support

For questions or issues, contact your CompliantFlow account representative.
