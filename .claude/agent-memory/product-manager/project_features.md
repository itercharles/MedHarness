---
name: CompliantFlow Feature Inventory
description: What is built and tested vs. what is planned or in progress
type: project
---

## Built and functional (as of 2026-04-03)

**Data layer (DHF/utils/)**
- Item CRUD: create/read/update/delete YAML items with auto-generated IDs (CR-006: IDs always auto-generated, caller-supplied IDs silently ignored)
- Git-backed persistence with atomic writes and commit history
- Schema validation: strict field validation per doc type at load time
- Lifecycle engine: state machine for CR, REL, DEF items with transition criteria
- Document generation: Jinja2 templates → Markdown → PDF via WeasyPrint
- Test result storage: `ResultStore` persists JUnit-parsed results to `DHF/test-results/results.yaml` (append-mode, full run history)
- GitHub Actions artifact fetcher: `utils test pull` command fetches CI artifacts via GitHub API
- JUnit XML parser: framework-agnostic boundary layer between tests and CompliantFlow
- Compliance run persistence: append-mode store under `DHF/compliance-runs/<standard_id>.yaml`

**Analysis engine (compliantflow/)**
- Traceability graph: NetworkX DiGraph with child→parent edge direction
- `build_traceability_matrix()`: multi-level matrix with orphan/completeness detection
- `get_item_chain()`: full connected subgraph for a single item
- `validate()`: orphan detection
- `check_coverage()`: per-pair coverage reporting
- Compliance engine: 10 automated check types (item_existence, file_existence, document_content, document_semantic via LLM, trace_coverage, attribute_presence, attribute_value, all_tests_passing, verification_complete, cr_git_evidence)
- LLM backend abstraction: `LLMBackend` protocol with `GeminiBackend` and `OllamaBackend` implementations; `get_default_backend()` picks based on env vars
- PolicyEngine instance cached per (group_id, governance_dir) on CompliantFlowCore
- PDF reports: traceability matrix PDF (with test results section) and compliance evidence PDF
- Verification status: computed from linked TC results (verified / failed / not_verified)
- Compliance run persistence: `check_compliance(..., persist=True)` appends run to DHF

**CLI surface**
- `python -m compliantflow`: validate traceability/coverage/compliance, traceability matrix/chain, report traceability/compliance PDF, cr check-status/generate-report, test import/status/list
- `python -m utils`: item CRUD, lifecycle transitions, schema validation, config doc-types, doc generate/export PDF, test import/status/list/pull

**CI/CD**
- Single CI pipeline (ci-pipeline.yml) with 5 phases:
  - Phase 0: CR validation gate (PR only) — validates CR ID in title, checks CR is approved/implementing
  - Phase 1: DHF utility tests
  - Phase 2: SYS API tests
  - Phase 3: CRS API tests
  - Phase 3.5: Generate merged CR-PR evidence report for all CRs
  - Phase 4: DHF validation, import test results, IEC 62304 + IEC 82304-1 compliance, PDF reports

**Governance**
- IEC 62304 policy file: 106 policies, 75 automated, 31 manual
- IEC 82304-1 policy file: 31 policies (20 automated, 11 manual with evidence_guidance)

**Doc types configured:** UC, CRS, SYS, SRS, SWDD, SYSARCH, CR, REL, DEF, RISK, RCM, SOUP

**Test coverage:** 98 tests (65 product sys/crs + 33 DHF utils), 2 skipped (weasyprint PDF)

## Notable gaps / weaknesses

- No GUI — all interaction is CLI; limits QA/RA personas (intentional for current ICP)
- No multi-tenant or multi-project support
- No authentication or access control
- Semantic compliance checks require GEMINI_API_KEY or OLLAMA running; air-gapped deployments need Ollama set up
- ISO 14971 governance file not yet written (v2.0.0 target)
- Release gate (REL items) not enforced by CLI (v2.0.0 target)
- Defect hook in CI not implemented (v2.0.0 target)
