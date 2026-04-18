# Getting Started with CompliantFlow v2.0.3

CompliantFlow is a **CI compliance gate** for medical device software projects.
It connects to your Design History File (DHF) and blocks merges that would
violate IEC 62304, ISO 14971, or ISO 13485 — before they land in your main branch.

---

## Quick Setup (recommended)

The fastest way to set up the full infrastructure is the interactive `init` command.
After installing (see Step 1), run:

```bash
compliantflow init
```

This single command will:
- Create a private DHF repository pre-configured with your project name and selected standards
- Open a pull request in your product repo adding the compliance CI gate
- Configure LLM API secrets for AI-assisted compliance checks (optional)

You will be prompted for each required piece of information. Nothing is committed or
created until you confirm the summary.

---

## Manual Setup

Use the steps below if you prefer to configure each component yourself, or if you
need a non-standard layout.

This guide covers:

1. Installing CompliantFlow in your CI pipeline
2. Setting up a DHF repository for your project
3. Running compliance checks locally during development

---

## Prerequisites

- Python 3.11 or later
- Git, a GitHub account, and the [GitHub CLI](https://cli.github.com) (`gh`)
- A product code repository (the repo CompliantFlow will gate)

---

## Step 1 — Install CompliantFlow

You will receive a `COMPLIANTFLOW_TOKEN` (GitHub PAT with `contents: read` access).
Add it to your repo secrets, then install in CI:

```yaml
- name: Install CompliantFlow
  env:
    GH_TOKEN: ${{ secrets.COMPLIANTFLOW_TOKEN }}
  run: |
    gh release download v2.0.3 --repo itercharles/CompliantFlow \
      --pattern "compliantflow-*.zip" \
      --output compliantflow.zip
    unzip compliantflow.zip -d cf
    pip install cf/*/build/compliantflow-*.whl
```

To install locally for development:

```bash
# One-time: authenticate with your token
gh auth login

gh release download v2.0.3 --repo itercharles/CompliantFlow \
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

## Step 2 — Create Your DHF Repository

The `dhf-template/` folder in this package is a ready-to-use Design History File.
Copy it into a new **private** Git repository for your project.

```bash
# Copy the template
cp -r dhf-template/ my-project-dhf
cd my-project-dhf

git init
git add .
git commit -m "initial DHF from CompliantFlow template"

# Push to GitHub (create the repo first at github.com — keep it private)
git remote add origin https://github.com/YOUR_ORG/my-project-dhf
git push -u origin main
```

Edit `DHF/config/global.yaml` to set your project name:

```yaml
project_name: "My Medical Device Software"
```

---

## Step 3 — Add the Compliance Gate to Your Product Repo

This is the core use case. Add this workflow to your **product code** repository:

```yaml
# .github/workflows/compliance.yml
name: Compliance Gate

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check out DHF
        uses: actions/checkout@v4
        with:
          repository: YOUR_ORG/my-project-dhf
          path: dhf
          token: ${{ secrets.DHF_REPO_TOKEN }}

      - name: Install CompliantFlow
        env:
          GH_TOKEN: ${{ secrets.COMPLIANTFLOW_TOKEN }}
        run: |
          gh release download v2.0.3 --repo itercharles/CompliantFlow \
            --pattern "compliantflow-*.zip" \
            --output compliantflow.zip
          unzip compliantflow.zip -d cf
          pip install cf/*/build/compliantflow-*.whl

      - name: Compliance gate
        run: |
          export PYTHONPATH="${PYTHONPATH}:${PWD}/dhf/DHF"
          compliantflow --dhf dhf/DHF validate traceability
          compliantflow --dhf dhf/DHF validate compliance IEC_62304 \
            --governance-dir dhf/governance
          compliantflow --dhf dhf/DHF validate coverage UC:CRS CRS:SYS SYS:SRS
```

Add these secrets to your product repo:
- `COMPLIANTFLOW_TOKEN` — provided by your CompliantFlow account representative (read access to the CompliantFlow release repo)
- `DHF_REPO_TOKEN` — a GitHub PAT with `repo` scope that can read your DHF repository

The compliance gate **blocks merges** when:
- Traceability links are broken or missing
- IEC 62304 / ISO 14971 policies are violated
- Coverage between item types falls below threshold

---

## Step 4 — Maintain Your DHF

As you develop, maintain DHF items alongside your code.
The DHF template includes a `utils` CLI for creating and updating items:

```bash
# From your DHF repo root
pip install click jinja2 markdown pydantic PyYAML gitpython

# Create a User Need
PYTHONPATH=.:DHF python -m utils item create --type UC \
  --data '{"title": "User needs compliance verification in CI"}'

# List all items
PYTHONPATH=.:DHF python -m utils item list

# Validate DHF schema
PYTHONPATH=.:DHF python -m utils validate schema
```

Item types available: `UC`, `CRS`, `SYS`, `SRS`, `SWDD`, `SYSARCH`, `RISK`, `RCM`, `SOUP`, `CR`, `REL`, `DEF`, `TC`

The DHF template also includes a CI workflow (`.github/workflows/ci.yml`) that validates
your DHF structure on every push and PR to the DHF repository.

---

## Step 5 — Local Compliance Checks (Development)

Run compliance checks locally before pushing, to catch failures early:

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

## Step 6 — AI-Assisted DHF Maintenance

The DHF template includes `CLAUDE.md` and `AGENTS.md` for Claude Code and compatible
AI coding tools. Open your DHF repository in Claude Code:

```bash
cd my-project-dhf
claude
```

The AI agent understands DHF item types, lifecycle rules, and compliance requirements,
and can help you create and validate DHF items correctly.

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

The `governance/` directory contains compliance policy files:

| File | Standard | Scope |
|---|---|---|
| `IEC_62304.yaml` | IEC 62304:2006+AMD1:2015 | Medical device software lifecycle |
| `ISO_14971.yaml` | ISO 14971:2019 | Risk management |
| `IEC_82304_1.yaml` | IEC 82304-1:2016 | Health software |
| `ISO_13485.yaml` | ISO 13485:2016 | Quality management systems |

Customise these files to match your project's applicable policies.

---

## Support

For questions or issues, contact your CompliantFlow account representative.
