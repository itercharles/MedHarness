# CompliantFlow

Compliance checking and Design History File (DHF) management for medical device software. Verifies IEC 62304, ISO 14971, and IEC 82304-1 in CI — every commit, automatically.

---

## What You Get

CompliantFlow is delivered as two components:

| Component | What it is | How to get it |
|---|---|---|
| **CompliantFlow CLI** | Read-only compliance analysis engine | `pip install compliantflow-X.Y.Z.whl` |
| **DHF Template** | Starter DHF with utils, config, governance, CI, and agent harness | Clone [compliantflow-dhf](https://github.com/itercharles/compliantflow-dhf) |

Together they form a complete compliance infrastructure: the CLI verifies, the DHF template stores and manages regulatory documentation.

---

## Getting Started (New Project)

### 1. Install the CLI

```bash
pip install compliantflow-2.0.0-py3-none-any.whl
```

### 2. Clone the DHF template as your project's DHF

```bash
git clone https://github.com/itercharles/compliantflow-dhf my-project-dhf
cd my-project-dhf
# Re-init as your own repo
rm -rf .git && git init && git add . && git commit -m "initial DHF from CompliantFlow template"
```

The DHF template includes:
- **`DHF/items/`** — starter item structure (UC, CRS, SYS, SRS, SWDD, RISK, RCM, CR types)
- **`DHF/config/`** — item type schemas and lifecycle definitions
- **`DHF/utils/`** — DHF mutation CLI (create items, transitions, schema validation)
- **`DHF/documents/`** — IEC 62304-required document templates (development plan, verification plan, etc.)
- **`governance/`** — ready-to-use compliance policy files for IEC 62304, ISO 14971, IEC 82304-1, ISO 13485
- **`.github/workflows/`** — CI workflow templates for DHF validation
- **`AGENTS.md` / `CLAUDE.md`** — AI coding agent harness for compliant AI-assisted development

### 3. Set up CI

Add to your GitHub Actions workflow:

```yaml
- name: Compliance gate
  run: |
    pip install compliantflow-2.0.0-py3-none-any.whl
    export PYTHONPATH="${PYTHONPATH}:${PWD}/dhf/DHF"
    compliantflow --dhf dhf/DHF validate compliance IEC_62304 --governance-dir dhf/governance
    compliantflow --dhf dhf/DHF validate traceability
    compliantflow --dhf dhf/DHF validate coverage UC:CRS CRS:SYS SYS:SRS
```

The gate exits with code 1 on any compliance failure, blocking non-compliant merges.

---

## Command Reference

```
compliantflow [--dhf PATH] COMMAND

Compliance validation:
  validate traceability           Check all items have upstream/downstream links
  validate compliance STANDARD    Run policy checks for a governance standard
  validate coverage PARENT:CHILD  Check coverage between item types
  validate release REL-ID         Evaluate release readiness
  validate draft FILE             Validate a draft item before creating it

Reporting:
  status                          At-a-glance compliance posture summary
  report compliance STANDARD      Generate compliance PDF report
  traceability matrix TYPES...    Build traceability matrix
  export submission               Assemble 510(k) submission evidence ZIP

Change management:
  cr check-status CR-ID           Check CR implementation status
  cr generate-report CR-ID        Generate CR evidence report

Test results:
  test import PATH                Import JUnit XML results
  test list                       List all test results
  test status TC-ID               Check a single test case

AI-assisted development:
  context                         Generate agent context package
  review-pr                       Compliance-aware PR review checklist

Migration:
  migrate rdm SOURCE_DIR          Migrate from Innolitics RDM
```

Run `compliantflow COMMAND --help` for full options.

---

## DHF Management

DHF mutations go through the `utils` CLI in your DHF repository:

```bash
# From your DHF repo root
PYTHONPATH=.:DHF python -m utils item list --type SYS
PYTHONPATH=.:DHF python -m utils item create --type SRS --data '{"title": "My requirement", "derives_from": ["SYS-001"]}'
PYTHONPATH=.:DHF python -m utils item transition CR-001 closed --by "Alice"
PYTHONPATH=.:DHF python -m utils validate schema
```

**CompliantFlow is read-only.** It analyses the DHF but never modifies it.

---

## 510(k) Submission Package

When all compliance gates pass, assemble the full evidence package:

```bash
compliantflow --dhf DHF export submission \
  --governance-dir governance \
  --output-dir ./submission
```

Produces `submission_YYYY-MM-DD.zip` containing:
- Cover document (FDA eSTAR section mapping)
- Traceability report PDF
- Compliance report PDFs (one per standard)
- SOUP list with vulnerability status
- RISK and RCM summary
- Test results summary
- CR evidence report

---

## Configuration

| Environment variable | Purpose |
|---|---|
| `COMPLIANTFLOW_DHF` | Default DHF path (overrides `--dhf`) |
| `COMPLIANTFLOW_LLM_BACKEND` | LLM backend: `gemini` or `ollama` |
| `GEMINI_API_KEY` | Required for Gemini backend |
| `COMPLIANTFLOW_OLLAMA_URL` | Ollama server URL (default: `http://localhost:11434`) |

---

## AI-Assisted Development

CompliantFlow ships with an AI coding agent harness. The DHF template includes `AGENTS.md` and `CLAUDE.md` pre-configured for Claude Code and compatible AI coding tools. This enables AI agents to create IEC 62304-compliant DHF items, understand lifecycle rules, and run compliance checks — with the CI gate confirming correctness automatically.

---

## For CompliantFlow Contributors

See [AGENTS.md](AGENTS.md) for the development workflow, CR process, and architecture.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
git clone https://github.com/itercharles/compliantflow-dhf
export PYTHONPATH=.:compliantflow-dhf/DHF
.venv/bin/pytest tests/ -q
```
