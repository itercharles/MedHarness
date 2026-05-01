# Getting Started with CompliantFlow

CompliantFlow is the open-source harness layer for design-controlled software
delivery. This guide covers installation, onboarding, and the first product-side
CI run. Canonical product requirements, architecture, and development-process
documents live in the DHF repo created from `CompliantFlow-DHF`.

---

## Prerequisites

- Python 3.11 or later
- [GitHub CLI](https://cli.github.com) (`gh`) installed and authenticated
- a product code repository on GitHub

---

## Step 1 — Install

### Local development install

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

CompliantFlow depends on `dhf_util`. Install the DHF substrate first, then the
harness package:

```bash
git clone https://github.com/compliantflow/compliantflow-dhf
cd compliantflow-dhf && pip install -e . && cd ..

gh release download --repo compliantflow/compliantflow \
  --pattern "compliantflow-*.whl"
pip install compliantflow-*.whl
```

---

## Step 2 — Run `compliantflow init`

`init` writes scaffold files locally. It fetches the DHF template from
`CompliantFlow-DHF` at runtime so the DHF repo starts from the current canonical
structure and documents.

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
| DHF template version (branch or tag) | `main` |
| Product repo local directory | `./insulin-pump` |
| Project name | `Insulin Pump Firmware` |

After confirmation, `init`:

- writes `CLAUDE.md`, `engineering-control.yml`, and `cr-complete.yml` into the product repo
- fetches the DHF scaffold and controlled document set from `CompliantFlow-DHF`
- applies project-name and repo-name substitutions in the fetched DHF content

---

## Step 3 — Review and Push

```bash
cd ./insulin-pump-dhf
git init && git remote add origin https://github.com/acme-medical/insulin-pump-dhf
git add -A && git commit -m "feat: initialize DHF"
git push -u origin main

cd ../insulin-pump
git checkout -b compliantflow/setup
git add CLAUDE.md .github/workflows/engineering-control.yml .github/workflows/cr-complete.yml
git commit -m "feat: add CompliantFlow harness and CI workflows"
git push -u origin compliantflow/setup
```

Add secrets after opening the PR:

| Repo | Secret | Value |
|------|--------|-------|
| Product repo | `DHF_REPO_TOKEN` | Fine-grained PAT with `Contents: Read` on the DHF repo |
| DHF repo | `PRODUCT_REPO_TOKEN` | Fine-grained PAT with `Contents: Write` on the product repo if CR completion pushes back |
| DHF repo | `ANTHROPIC_API_KEY` | Required only if DHF-side AI workflows are enabled |

---

## Step 4 — Use the DHF as the Canonical Source

The DHF repo is where formal product documents live. The canonical documents are:

- `DHF/documents/specs/customer_requirement_specification.md`
- `DHF/documents/specs/architecture_design_specification.md`
- `DHF/documents/plans/development_plan.md`

When product direction, architecture boundaries, or development/testing process
changes, update those DHF-side documents through the CR workflow instead of
creating parallel strategy docs in the product repo.

---

## Step 5 — Run Checks Locally

Before pushing, run the relevant tests and coverage gate locally:

```bash
pytest tests/ -q --junitxml=test-results/results.xml
compliantflow --dhf DHF ci test-coverage --junit-dir test-results
```

If you are working in the DHF repo directly, also run:

```bash
python -m dhf_util --dhf DHF validate traceability
```

---

## Support

- File a [GitHub Issue](https://github.com/compliantflow/compliantflow/issues)
- See [SUPPORT.md](SUPPORT.md)
