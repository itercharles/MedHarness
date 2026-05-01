# Getting Started with CompliantFlow

CompliantFlow is an open-source design-controlled development harness for
medical device software. This guide walks through install, project scaffolding,
and first CI run.

---

## Prerequisites

- Python 3.11 or later
- [GitHub CLI](https://cli.github.com) (`gh`) installed and authenticated
- A product code repository on GitHub (can be empty)

---

## Step 1 — Install

### Local development install (recommended)

```bash
git clone https://github.com/compliantflow/compliantflow
cd CompliantFlow
pip install -e .
```

Verify:

```bash
compliantflow --help
```

### Released package install

Download the latest release from GitHub Releases:

```bash
gh release download --repo compliantflow/compliantflow \
  --pattern "compliantflow-*.whl"
pip install compliantflow-*.whl
```

PyPI distribution is planned but not yet available.

---

## Step 2 — Run `compliantflow init`

This command writes all required files locally. No GitHub operations are
performed — you review and push everything yourself.

```bash
compliantflow init
```

You will be prompted for:

| Prompt | Example |
|--------|---------|
| GitHub org or username | `acme-medical` |
| Product repository name | `insulin-pump` |
| Set up a DHF repository? | `Y` |
| DHF repository name | `insulin-pump-dhf` |
| Local directory for DHF files | `./insulin-pump-dhf` |
| Product repo local directory | `./insulin-pump` |
| Project name (for documents) | `Insulin Pump Firmware` |
| Applicable standards | IEC 62304, ISO 14971 |

After you confirm, `init` writes:

- **DHF template** → your specified DHF local directory, pre-configured with
  project name and selected standards
- **`CLAUDE.md`** → your product repo local directory, with minimal repo
  guidance and links to canonical docs
- **`.github/workflows/engineering-control.yml`** → your product repo local directory,
  with test-coverage CI gate

`init` then prints the exact git commands to push both repos and open a PR.

---

## Step 3 — Review, push, and open a PR

After `init` completes, follow the printed instructions:

```bash
# 1. Push DHF repo
cd ./insulin-pump-dhf
git init && git remote add origin https://github.com/acme-medical/insulin-pump-dhf
git add -A && git commit -m "feat: initialize DHF"
git push -u origin main

# 2. Open engineering control PR in product repo
cd ./insulin-pump
git checkout -b compliantflow/setup
git add CLAUDE.md .github/workflows/engineering-control.yml .github/workflows/cr-complete.yml
git commit -m "feat: add CompliantFlow harness and CI workflows"
git push -u origin compliantflow/setup
```

Then open a pull request and add the required secrets (Settings → Secrets → Actions):

**Product repo:**

| Secret | Value |
|--------|-------|
| `DHF_REPO_TOKEN` | Fine-grained PAT with `Contents: Read` on your DHF repo |

**DHF repo (if separate):**

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | API key for DHF AI workflows (`cr-analyze`, `cr-spec-iterate`, `cr-develop`) |
| `PRODUCT_REPO_TOKEN` | Fine-grained PAT with `Contents: Write` access to your product repo |

Merge the PR. From that point on, every push and PR in your product repo is
checked against:

- Test coverage (requirement → test traceability)
- Design traceability links (no orphaned requirements in the DHF)

---

## Step 4 — Maintain your DHF

Open your DHF repository in Claude Code to create and update items with AI
assistance:

```bash
gh repo clone YOUR_ORG/YOUR_PRODUCT-dhf
cd YOUR_PRODUCT-dhf
claude
```

The DHF includes structured DHF config and item templates — so AI agents
item types, lifecycle rules, and traceability requirements out of the box.

To manage items manually:

```bash
# Install DHF utils dependencies (from the DHF repo root)
pip install click jinja2 markdown pydantic PyYAML gitpython

# Create a System Requirement
python -m dhf_util --dhf DHF item create --type SYS \
  --data '{"title": "System shall validate all inputs", "category": "Functional"}'

# List all items
python -m dhf_util --dhf DHF item list

# Validate DHF schema
python -m dhf_util --dhf DHF validate schema
```

---

## Step 5 — Run traceability checks locally

Before pushing, run checks locally to catch failures early:

```bash
# Requirement → test coverage gate
compliantflow --dhf DHF ci test-coverage --junit-dir test-results

# Design traceability posture
compliantflow --dhf DHF status
```

---

## Command Reference

```
compliantflow [--dhf PATH] COMMAND

Setup:
  init                            Interactive infrastructure onboarding

CI gates (stable OSS):
  ci test-coverage                Requirement → test coverage gate
  ci evidence bundle              Produce CI evidence bundle
  ci release consume-artifact     Download CI artifact (gh CLI)
  ci release assemble             Assemble release bundles

Traceability:
  validate traceability           Check all items have upstream/downstream links
  validate coverage PARENT:CHILD  Check coverage between item types (e.g. UC:CRS)
  status                          At-a-glance design traceability posture

Change management:
  cr check-status CR-ID           Check CR implementation status
  cr generate-report CR-ID        Generate CR evidence report

Tests:
  test import PATH                Import JUnit XML results into DHF
  test list                       List all test results
  test status TC-ID               Check a single test case

AI tools:
  context                         Generate agent context package
  review-pr                       Traceability-aware PR review checklist

Migration:
  migrate rdm SOURCE_DIR          Migrate from Innolitics RDM
```

---

## Support

For questions or issues:
- File a [GitHub Issue](https://github.com/compliantflow/compliantflow/issues)
- See [SUPPORT.md](SUPPORT.md) for additional support channels
