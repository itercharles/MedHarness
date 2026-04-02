---
name: CompliantFlow Feature Inventory
description: What is built and tested vs. what is planned or in progress
type: project
---

## Built and functional (as of 2026-04-02)

**Data layer (DHF/utils/)**
- Item CRUD: create/read/update/delete YAML items with auto-generated IDs
- Git-backed persistence with atomic writes and commit history
- Schema validation: strict field validation per doc type at load time
- Lifecycle engine: state machine for CR, REL, DEF items with transition criteria
- Document generation: Jinja2 templates → Markdown → PDF via WeasyPrint
- Test result storage: `ResultStore` persists JUnit-parsed results to `results.yaml`
- GitHub Actions artifact fetcher: `test pull` command fetches CI artifacts via GitHub API
- JUnit XML parser: framework-agnostic boundary layer between tests and CompliantFlow

**Analysis engine (compliantflow/)**
- Traceability graph: NetworkX DiGraph with child→parent edge direction
- `build_traceability_matrix()`: multi-level matrix with orphan/completeness detection
- `get_item_chain()`: full connected subgraph for a single item
- `validate()`: orphan detection
- `check_coverage()`: per-pair coverage reporting
- Compliance engine: 8 automated check types (item_existence, file_existence, document_content, document_semantic via Gemini, trace_coverage, attribute_presence, attribute_value, all_tests_passing, verification_complete)
- PDF reports: traceability matrix PDF and compliance evidence PDF (WeasyPrint)
- Verification status: computed from linked TC results (verified / failed / not_verified)

**CLI surface**
- `python -m compliantflow`: validate traceability, validate coverage, validate compliance, traceability matrix, traceability chain, report traceability (PDF), report compliance (PDF)
- `python -m utils`: item CRUD, lifecycle transitions, schema validation, config doc-types, doc generate, doc export (PDF), test import, test pull, test status, test list

**Governance**
- IEC 62304 policy file: 106 policies, 75 automated, 31 manual
- IEC 82304-1 policy file: partial

**Doc types configured:** UC, CRS, SYS, SRS, SWDD, SYSARCH, CR, REL, DEF, RISK, RCM, SOUP

**Test coverage:** sys/ (API tests for core engine), crs/ (scenario tests for CRS-002, CRS-008, CRS-011), DHF/utils/tests/ (data layer unit/CLI tests)

## Notable gaps / weaknesses identified

- No web UI — all interaction is CLI. This significantly narrows usability for non-technical QA/RA users.
- No multi-tenant or multi-project support — single DHF directory per deployment
- No authentication or access control
- No real-time collaboration or locking
- Semantic compliance checks (Gemini) require GEMINI_API_KEY — no fallback/alternative for air-gapped environments
- IEC 82304-1 governance file is partial / incomplete
- REL-002 (v1.1.0) has no included items — release process is underused
- CR-006 (auto ID generation, in_review) points to a UX gap where IDs are currently editable
- DEF-001 is a sample/placeholder defect — defect tracking is set up but barely populated
- Only 3 UCs, 3 CRS, 6 SYS requirements tracked — DHF is sparse relative to a real product DHF
- Test suite uses Chinese-language README, suggesting the team may be distributed/international
