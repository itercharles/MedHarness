# Change Request Specification

**Document Version:** 1.0  
**Generated:** 2026-04-06  
**Project:** CompliantFlow Project

---

## Document Control

| Field | Value |
|-------|-------|
| Document ID | CR-SPEC |
| Version | 1.0 |
| Status | DRAFT |
| Last Updated | 2026-04-06 |
| Total Change Requests | 33 |

---

## Purpose

This document provides a comprehensive specification of all Change Requests (CRs) in the system. Each CR tracks proposed changes to the product, including their justification, impact assessment, implementation status, and affected items.

---

## Change Request Summary

### By Status

- **PLANNED**: 6 change request(s)
- **COMPLETED**: 24 change request(s)

### By Priority

- **High**: 15 change request(s)
- **Medium**: 14 change request(s)
- **Low**: 1 change request(s)

---

## Change Requests


### CR-001: Add bulk approval feature for requirements

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Quality Team  
**Assigned To:** 

#### Description

Currently, requirements must be approved one at a time, which is inefficient when
processing large batches of requirements. This change request proposes adding a
bulk approval feature that allows selecting multiple requirements and approving
them all at once.


#### Justification

- Improves efficiency when approving large batches of requirements
- Reduces time spent on repetitive approval tasks
- Maintains audit trail for each individual approval
- Common feature request from quality team


#### Impact Assessment

**UI Changes:**
- Add checkbox column to requirements table
- Add "Bulk Actions" dropdown with "Approve Selected" option
- Add confirmation dialog showing list of items to be approved
**Backend Changes:**
- Extend workflow engine to support batch operations
- Ensure each item's approval is recorded individually
- Maintain complete audit trail
**Testing:**
- Add test cases for bulk approval functionality
- Verify individual approval records are created
- Test with various batch sizes
**Risk Assessment:** Low
- Isolated feature addition
- No changes to existing approval logic
- Can be feature-flagged if needed


#### Affected Items

- SYS-001
- SYSARCH-001
- TC-API-001
- TC-API-003
- TC-API-004
- TC-API-005
- TC-API-008
- TC-API-010



#### Traceability




---


### CR-003: Automated PR-CR Linking and Traceability System

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Compliance Team  
**Assigned To:** Development Team

#### Description

Implement automated workflows to link Pull Requests to Change Requests, ensuring 
complete traceability and regulatory compliance.

**Objectives:**
- Enforce CR references in all PRs
- Automatically detect and record affected DHF items
- Track PR implementation in CRs
- Maintain complete audit trail for regulatory compliance

**Scope:**
- GitHub Actions workflows for PR validation
- Automated affected items detection
- PR status tracking throughout lifecycle
- CR data model extensions


#### Justification

**Regulatory Requirement:**
IEC 62304 §6.2 (Change Control) and FDA 21 CFR 820.30(i) require documented 
linkage between code changes and change requests.

**Current Gap:**
Manual tracking is error-prone and does not scale. Automated enforcement ensures 
100% compliance and complete traceability.

**Benefits:**
- Guaranteed regulatory compliance
- Complete audit trail
- Reduced manual effort
- Improved change management process


#### Impact Assessment

**Affected Systems:**
- GitHub repository workflows
- CR document type configuration
- Development workflow
**Risk Assessment:**
- **Technical Risk:** Low - Uses standard GitHub Actions
- **Process Risk:** Medium - Requires team adoption of new workflow
- **Compliance Risk:** Low - Improves compliance posture
**Mitigation:**
- Comprehensive testing before enforcement
- Team training on new workflow
- Clear error messages for validation failures


#### Affected Items

- SYS-030
- SRS-021
- SWAD-011
- SWDD-020
- SWDD-021
- SWDD-022
- RISK-001
- RCM-001
- CRS-010
- CRS-011
- SYS-001
- SYS-002
- SYS-003
- SYS-004
- SYS-005
- SYS-006
- SYS-007
- SYS-008
- SYS-009
- SYS-010
- SYS-011
- SYS-012
- SYS-013
- SYS-014
- SYS-015
- SYS-016
- SYS-017
- SYS-018
- SYS-019
- SYS-020
- SYS-021
- SYS-022
- SYS-023
- SYS-024
- SYS-025
- SYS-026
- SYS-027
- SYS-028
- SYS-029
- SYSARCH-001
- DEF-001
- REL-1.0.0
- REL-1.1.0
- REL-1.2.0
- UC-001
- UC-002
- UC-003
- UC-004
- UC-005
- CRS-001
- CRS-002
- CRS-003
- CRS-004
- CRS-008
- SYS-031
- SRS-001
- SRS-002
- SRS-003
- SRS-004
- SRS-005
- SRS-006
- SRS-007
- SRS-008
- SRS-009
- SRS-010
- SRS-011
- SWDD-001
- SWDD-002
- SWDD-003
- SWDD-004
- SWDD-005
- SWDD-006
- SWDD-007
- SWDD-008
- SWDD-009
- SWDD-010
- SWDD-011
- SWDD-012
- SYSARCH-002
- SYSARCH-003
- SYSARCH-004
- SYSARCH-005
- SYSARCH-006
- SYSARCH-007
- SYSARCH-008
- TC-SRS-001
- TC-SRS-002
- TC-SRS-003
- TC-SRS-005
- TC-SRS-006
- TC-SRS-007
- TC-SRS-008
- TC-SRS-010
- TC-SRS-011
- TC-SRS-012
- TC-SRS-013
- TC-SRS-015
- TC-SRS-021
- TC-SYS-001
- TC-SYS-003
- TC-SYS-004
- TC-SYS-005
- TC-SYS-008
- TC-SYS-010
- TC-SYS-021
- TC-SYS-031



#### Traceability




---


### CR-004: Improve the format customization of frontend style

**Status:** COMPLETED  
**Priority:** Not Set  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- TC-SRS-014
- TC-SRS-016
- TC-SYS-007
- TC-SYS-024



#### Traceability




---


### CR-005: Improve the effectiveness of the auto testing

**Status:** COMPLETED  
**Priority:** Not Set  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- TC-SDS-001



#### Traceability




---


### CR-006: The objects' ID shall be generated automatically and not editable

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Claude

#### Description

The objects' ID shall be generated automatically and not editable

#### Justification

The ID shall not be edit as it cause problems for the reference

#### Impact Assessment

Remove caller-supplied ID path in create_item. No schema or YAML format changes. Existing items unaffected. Tests updated to use ItemSaver directly for fixture data with stable IDs.

#### Affected Items

- SRS-001
- TC-SRS-002
- TC-SYS-008
- TC-SYS-010



#### Traceability




---


### CR-007: Defect: the specification generation in system architecture page doesn't work

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

The error pop up when trying to generating the specification document in the system architecture page. 

#### Justification

defect

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- TC-SRS-007
- TC-SRS-011
- TC-SRS-021



#### Traceability




---


### CR-010: Centralize Relationship Configuration

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Claude

#### Description

Centralize relationship type configuration into a global registry in ProjectConfig, replacing per-doc-type relationship definitions with shared RelationshipType models and validation.

#### Justification

Relationship types were duplicated across doc type configs. Centralizing them reduces inconsistency and enables relationship metadata to be used programmatically across the compliance engine.

#### Impact Assessment

Added RelationshipType model to schema, relationship_types global registry to ProjectConfig, validation for relationship_type references, and migrated CR doc type as proof of concept. All tests pass.

#### Affected Items

- CR-009



#### Traceability




---


### CR-011: refactor the status management of object

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Current status definition is too complex and should be simplified. 

There should be a collection of all the lifecycle status and action in the configuration - 
action: create -> status: draft
action: submit for review -> status: in review 
action: approve -> status: approved 
action: start implementation -> status: implementing 
action: complete -> status: completed
action: start verification -> status: verified
action: start validation -> status validated
action: acceptance assessment -> status accept
action: retire -> status: retired
action: close -> status: closed

Then, for each object, the property can be configured:
name: lifecycle_status
current_status: none
support_actions:
- create
current_status: draft
support_actions:
- approve
- retire
current_status: approved
support_actions:
- retire

And, every action shall recorded as atom data, including who and when this change is performed. This is not necessary to be configured, it's a forced policy.

#### Justification

unify the status management.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- TC-SRS-006
- TC-SRS-008
- TC-SRS-015
- UC-001
- UC-002
- UC-003
- UC-004
- UC-005
- UC-006
- CRS-001
- CRS-002
- CRS-003
- CRS-004
- CRS-008
- CRS-011
- CRS-013
- SYS-001
- SYS-003
- SYS-004
- SYS-005
- SYS-008
- SYS-010
- SYS-021
- SYS-030
- SYS-031
- SYS-032
- SYS-033
- SRS-001
- SRS-002
- SRS-003
- SRS-004
- SRS-005
- SRS-006
- SRS-007
- SRS-008
- SRS-009
- SRS-010
- SRS-011
- SRS-012
- SRS-013
- SWDD-001
- SWDD-002
- SWDD-003
- SWDD-004
- SWDD-005
- SWDD-006
- SWDD-007
- SWDD-008
- SWDD-009
- SWDD-010
- SWDD-011
- SWDD-012
- SWDD-013
- SWDD-014
- SWDD-015
- SWDD-016
- SYSARCH-001
- SYSARCH-002
- SYSARCH-003
- SYSARCH-004
- SYSARCH-005
- SYSARCH-006
- SYSARCH-007
- SYSARCH-008
- SYSARCH-009
- SYSARCH-010
- SOUP-PYDANTIC-2.0.0
- SOUP-STREAMLIT-1.28.0
- RISK-001
- RCM-001
- TC-SRS-002
- TC-SRS-021
- TC-SYS-001
- TC-SYS-010
- TC-SYS-031
- TC-SYS-032



#### Traceability




---


### CR-012: Add CLI layer for CI/CD integration

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Add a command-line interface (CLI) package `src/compliantflow/` so that CI/CD
pipelines and external tools can invoke CompliantFlowCore operations without
starting the Streamlit web UI.
This replaces the fragile inline Python scripts in Phase 4 of the CI pipeline
with proper CLI commands that reuse the existing business logic layer.

#### Justification

The current CI Phase 4 bypasses CompliantFlowCore by directly reading and writing
YAML files. This duplicates logic, is hard to test, and breaks when the data model
changes. A proper CLI layer ensures CI/CD uses the same validated code path as the UI.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- UC-006
- SYS-032
- SRS-012
- SYSARCH-009
- SWDD-013
- TC-SYS-032
- TC-SRS-002
- TC-SRS-006
- TC-SRS-010
- TC-SRS-013
- TC-SRS-015
- TC-SYS-001
- TC-SYS-002
- TC-SYS-003
- TC-SYS-004
- TC-SYS-005
- TC-SYS-008
- TC-SYS-010
- TC-SYS-021
- TC-SYS-031
- TC-SRS-012
- SYS-033
- TC-SYS-033
- SRS-010
- SWDD-012
- SYSARCH-007
- UC-001
- UC-002
- UC-003
- UC-004
- UC-005
- REL-003
- CRS-001
- CRS-008
- CRS-013
- SYS-001
- SYS-010
- SYS-031
- SRS-013
- SWDD-002
- SWDD-003
- SWDD-005
- SWDD-007
- SWDD-009
- SWDD-014
- SWDD-015
- SOUP-PYDANTIC-2.0.0
- SOUP-STREAMLIT-1.28.0



#### Traceability




---


### CR-013: Split DHF data layer from CompliantFlow analysis engine

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Extract the DHF data layer into a standalone `src/dhf/` package and introduce a `DHFAdapter` interface so any backend can plug into CompliantFlow.
Key changes:
- Split `DHF/config/project_config.yaml` into `global.yaml` + per-doc-type files under `DHF/config/doc_types/`
- New `src/dhf/` package: models, repository, result_store, document_generation, and standalone CLI (`python -m dhf`)
- New `src/compliantflow/adapters/`: `DHFAdapter` Protocol + `LocalDHFAdapter`
- `CompliantFlowCore` accepts any `DHFAdapter`; defaults to `LocalDHFAdapter`
- CompliantFlow CLI trimmed to analysis-only; data CRUD moved to DHF CLI
- `src/cli/cli.py` moved into `src/compliantflow/cli.py` for symmetry with `src/dhf/cli.py`

#### Justification

CompliantFlow bundles data management (YAML CRUD, schema, doc generation) and analysis (graph, traceability, compliance, lifecycle) in one package. Separating them allows the DHF data layer to be used independently, enables alternative backends via the adapter interface, and makes each package easier to test and reason about in isolation.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-001
- SYS-010
- SYS-021
- SYS-032
- SRS-001
- SRS-003
- TC-SRS-001
- TC-SRS-002
- TC-SRS-003
- TC-SRS-005
- TC-SRS-007
- TC-SRS-008
- TC-SRS-010
- TC-SRS-011
- TC-SYS-002
- TC-SYS-004
- TC-SYS-008
- TC-SYS-010
- TC-SYS-032
- TC-SYS-033



#### Traceability




---


### CR-014: Move DHF data layer and test results into DHF/utils/

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Relocate the standalone data-layer package and test-result integration into the DHF directory tree, co-locating code with the data it manages.
Key changes:
- `src/dhf/` → `DHF/utils/` (data-layer package now lives inside DHF)
- `src/test_results/junit_parser.py` → `DHF/utils/junit_parser.py` (dissolved src/test_results/ package; junit_parser joins result_store.py in DHF/utils/)
- `src/utils/` → `src/helpers/` (renamed to avoid Python package name collision with DHF/utils/)
- All `from dhf.` imports updated to `from utils.`; `from utils.*helpers*` imports updated to `from helpers.`
- PYTHONPATH updated from `src` to `src:DHF` across CLAUDE.md, CI pipeline, and test commands
- CLI entry point for data operations: `python -m utils` (was `python -m dhf`)
- Design files updated: SWDD-013, SWDD-012, SYSARCH-007, SYSARCH-009

#### Justification

The DHF directory is the authoritative home for all design history artefacts. Co-locating the data-layer tooling (utils/) with the data it manages (items/, config/, test-results/) makes the DHF self-contained — it can be used as a standalone repository without the analysis engine.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-032
- SWDD-012
- SWDD-013
- SYSARCH-007
- SYSARCH-009
- TC-SRS-001
- TC-SRS-002
- TC-SRS-003
- TC-SRS-005
- TC-SRS-007
- TC-SRS-008
- TC-SRS-010
- TC-SRS-011
- TC-SRS-013
- TC-SYS-002
- TC-SYS-004
- TC-SYS-008
- TC-SYS-010
- TC-SYS-032
- TC-SYS-033
- TC-SYS-005



#### Traceability




---


### CR-015: Fix adapter abstraction — remove loader/saver leakage and add DHF test CLI

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Two targeted fixes to the DHF/CompliantFlow boundary:

1. Remove loader/saver shortcut properties from CompliantFlowCore.
   These exposed LocalDHFAdapter internals (_loader, _saver) through the
   core facade and would break silently for any non-local adapter.
   Tests that needed raw loader/saver access now use core._adapter directly,
   making the LocalDHFAdapter dependency explicit and honest.

2. Add `test status` and `test list` commands to the DHF CLI (python -m utils).
   Test results are DHF-owned data (DHF/test-results/results.yaml).
   Read operations belong in the DHF CLI alongside item/validate/doc.
   `test import` stays in the CompliantFlow CLI because it orchestrates
   JUnit XML parsing + ResultStore writes + verification_status updates
   (which require the analysis graph engine).

#### Justification

The loader/saver properties violated the DHFAdapter abstraction by coupling
CompliantFlowCore to LocalDHFAdapter implementation details. Any alternative
adapter (cloud, database, API) would fail silently at runtime.
Moving test result reads to the DHF CLI correctly models ownership:
compliance data is core-system-owned (governance/ at repo root);
test results are DHF-owned (DHF/test-results/results.yaml).

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-032
- SRS-001
- TC-SRS-001
- TC-SRS-002
- TC-SRS-005
- TC-SRS-008
- TC-SRS-011
- TC-SYS-002
- TC-SYS-008
- TC-SYS-010



#### Traceability




---


### CR-016: Consolidate src/ — move traceability/ and helpers/ into compliantflow/, app.py into debug_view/

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Two structural changes to clean up the src/ layout:

1. Move src/traceability/ → src/compliantflow/traceability/
   Move src/helpers/     → src/compliantflow/helpers/
   Rationale: traceability/ and helpers/ are internal dependencies of the
   compliantflow analysis engine. Exposing them as sibling top-level packages
   in src/ allowed any code to import them directly, bypassing the intended
   public API (CompliantFlowCore). Moving them inside compliantflow/ makes
   the package boundary explicit.

2. Move src/app.py → src/debug_view/app.py
   Rationale: app.py is the Streamlit entry point for the debug UI. It only
   loads debug_view/ pages and has no purpose outside that context. Co-locating
   it with the pages it orchestrates makes debug_view/ self-contained.
   Run command updated to: streamlit run src/debug_view/app.py

All internal imports updated:
- from traceability.* → from compliantflow.traceability.*
- from helpers.*      → from compliantflow.helpers.*
- Path calculations in app.py adjusted for new directory depth

#### Justification

src/ previously exposed three separate top-level packages (compliantflow,
traceability, helpers) when only compliantflow should be the public interface.
This CR makes compliantflow the single top-level package in src/, with
traceability and helpers as internal sub-packages, matching the intended
architecture described in the design.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-021
- TC-SRS-001
- TC-SRS-002
- TC-SRS-007
- TC-SRS-008
- TC-SRS-011
- TC-SRS-012
- TC-SRS-013
- TC-SYS-032



#### Traceability




---


### CR-017: Remove PR metadata from CR YAML — use GitOps-implicit linkage

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Design Review  
**Assigned To:** Unassigned

#### Description

Change Requests currently store pr_number, pr_url, and pr_title in an
implementation_prs list that CI writes automatically on every PR open/synchronize
event. This creates three problems:

1. Stale data: if a PR is closed without merging (abandoned, re-opened with a
   new number, or retitled), the YAML retains incorrect information.
2. Sync friction: CI commits to feature branches (Phase 4) can race with
   developer commits, trigger re-runs, and complicate rebase workflows.
3. Redundancy: PR title already starts with CR-NNN (enforced by CI), branch
   naming follows feature/cr-NNN-*, and commit messages carry the prefix.
   The PR is already discoverable by searching GitHub for the CR ID — storing
   it again in YAML adds noise, not value.

The fix is to treat PR linkage as GitOps-implicit (same model as requirement-item
approval) and stop writing PR metadata into CR YAML files.

#### Justification

The GitOps approval model (SYSARCH-010) established that Git itself is the
source of truth for approval evidence on requirement items. The same principle
applies here: Git history already records the PR-CR association via title
conventions and branch names. Writing it again into YAML duplicates data,
creates a stale-data hazard, and causes CI write conflicts.

#### Impact Assessment

- CLI: remove --pr-number, --pr-url, --pr-title from `cr update` command
- CI Phase 4: remove those flags from the cr update call in ci-pipeline.yml
- CR doc type config: remove implementation_prs property
- Existing CR YAML files: implementation_prs fields remain (backwards compatible,
  schema validation uses extra='ignore' for unknown fields); no migration needed
- SYSARCH-011 and SWDD-017 document the architectural rationale

#### Affected Items

- SYSARCH-011
- SWDD-017
- SYS-032
- TC-SYS-032



#### Traceability




---


### CR-018: Define component boundaries — DHF / compliantflow / tests

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Architecture Review  
**Assigned To:** Unassigned

#### Description

The three-component architecture (DHF data layer, compliantflow analysis
engine, and test suites) has been implemented across multiple CRs (CR-013 through
CR-017) but the boundaries between them have never been formally documented or
enforced. This creates three problems:

1. Import violations: compliantflow CLI directly imports utils.junit_parser, bypassing
   the DHFAdapter protocol it was designed to encapsulate.
2. Private attribute access: SRS tests access test_core._adapter._loader (a private
   attribute) to obtain Item objects, coupling tests to adapter internals.
3. No public API contract: DHF/utils/__init__.py is empty, making it unclear which
   symbols are intended for external use vs internal implementation.

This CR defines the component boundary rules formally, fixes the existing violations,
and adds a CI-enforced boundary test.

#### Justification

Formal boundary definitions are required for IEC 62304 software architecture documentation
(section 5.3) and to prevent regression as the codebase evolves. The fix is also
prerequisite for safely substituting alternative DHF backends via the adapter protocol,
since boundary violations make the adapter effectively non-swappable.

#### Impact Assessment

- New architecture doc (SYSARCH-012) and implementation spec (SWDD-018)
- New SYS requirement SYS-034 with test enforcement
- DHF/utils/__init__.py: add explicit public exports
- DHFAdapter protocol: add import_results_from_file() method
- LocalDHFAdapter: implement import_results_from_file()
- compliantflow CLI: remove direct utils.junit_parser import
- 11 SRS test files: replace _adapter._loader private access with direct ItemLoader usage
- New test: tests/sys/test_sys_034_boundary.py

#### Affected Items

- SYSARCH-012
- SWDD-018
- SYS-034



#### Traceability




---


### CR-019: Test results — GitHub Actions artifacts as source of truth

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Architecture Review  
**Assigned To:** Unassigned

#### Description

CI Phase 3.5 automatically committed DHF/test-results/results.yaml back to the
PR branch after each test run. This created three problems:

1. Anti-pattern: CI modified the branch it was testing, violating the principle
   that CI should only read the repo, not write to it.
2. Push conflicts: because CI committed to the feature branch, developers needed
   to rebase before pushing (git push rejected due to non-fast-forward).
3. Redundant data: results.yaml was a derived copy of GitHub Actions artifacts,
   adding no independent value — the artifacts are already the authoritative record.

This CR removes Phase 3.5 entirely. GitHub Actions artifacts are the sole source
of truth for test execution results. A new 'test pull' CLI command fetches results
from artifacts on demand via the GitHub API (GITHUB_TOKEN required). The DHF layer
encapsulates all GitHub API details via GitHubArtifactFetcher, keeping CompliantFlow
agnostic to the storage backend.

#### Justification

Removing CI writes simplifies the pipeline, eliminates push conflicts, and enforces
the clean boundary defined in CR-018: DHF owns all data I/O, CompliantFlow only
analyses. IEC 62304 traceability is preserved — each test result carries a GitHub
Actions run URL and commit SHA, which constitute the audit trail.

#### Impact Assessment

- CI pipeline: Phase 3.5 job removed; permissions downgraded from contents:write to contents:read
- New: DHF/utils/artifact_fetcher.py (GitHubArtifactFetcher — all GitHub API logic)
- DHFAdapter protocol: new pull_results_from_artifacts() method
- LocalDHFAdapter: implements pull_results_from_artifacts() via GitHubArtifactFetcher
- test_results_mixin: new pull_test_results() + _inject_verification_status() (in-memory, no YAML write)
- CLI: new 'test pull' subcommand
- DHF/test-results/results.yaml: removed from git, added to .gitignore (local cache only)

#### Affected Items

- SYSARCH-013
- SYS-035



#### Traceability




---


### CR-020: Separate DHF utility docs and tests from product DHF

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Architecture Review  
**Assigned To:** Unassigned

#### Description

DHF/items/ should document what CompliantFlow does for users (product
requirements, architecture, design). Approximately 32 items (SRS, SWDD,
SYSARCH, SYS) described internal DHF/utils/ infrastructure — YAML I/O,
graph engine, schema validation, document generation, test result parsing —
which has no place in the product DHF.

Similarly, tests/srs/ tested the DHF data layer directly (ItemLoader,
ItemSaver, GraphEngine, ResultStore), not CompliantFlow product behaviour.
These belong with the code they test.

This CR:
1. Removes 32 DHF-utility items from DHF/items/.
2. Consolidates their content into DHF/utils/docs/ as Markdown
   (requirements.md, architecture.md, design.md, README.md).
3. Moves tests/srs/ → DHF/utils/tests/ (co-located with the package).
4. Moves 3 product-behaviour tests from tests/srs/ → tests/sys/.
5. Updates CI pipeline Phase 1 to run DHF/utils/tests/.

#### Justification

A product DHF for a medical device should trace user needs through customer
and system requirements to software design. Internal data-layer plumbing
(how YAML files are loaded, how the graph is built) is implementation detail,
not product documentation. Mixing them inflates the DHF, creates false
traceability gaps, and makes compliance reviews harder.

Moving the tests co-locates them with the code under test (DHF/utils/),
following standard Python packaging convention and making the boundary
between product tests and data-layer tests explicit.

#### Impact Assessment

- Deleted from DHF/items/: SRS-001–005, SRS-008–011, SWDD-001–006,
  SWDD-009–012, SWDD-014, SWDD-016, SWDD-018, SYSARCH-001–003,
  SYSARCH-005–007, SYSARCH-010, SYSARCH-012, SYS-033, SYS-034
- New: DHF/utils/docs/README.md, requirements.md, architecture.md, design.md
- Moved: tests/srs/ → DHF/utils/tests/ (with new conftest.py + fixtures.py)
- Moved to tests/sys/: test_sys_012_streamlit.py, test_sys_013_hyperlinks.py,
  test_sys_021_pr_cr_automation.py
- Updated: CLAUDE.md (test commands), ci-pipeline.yml (Phase 1 target)
- SWDD-017.yaml: removed obsolete implements: SRS-001 link

#### Affected Items

- SRS-001
- SRS-002
- SRS-003
- SRS-004
- SRS-005
- SRS-008
- SRS-009
- SRS-010
- SRS-011
- SWDD-001
- SWDD-002
- SWDD-003
- SWDD-004
- SWDD-005
- SWDD-006
- SWDD-009
- SWDD-010
- SWDD-011
- SWDD-012
- SWDD-014
- SWDD-016
- SWDD-018
- SYSARCH-001
- SYSARCH-002
- SYSARCH-003
- SYSARCH-005
- SYSARCH-006
- SYSARCH-007
- SYSARCH-010
- SYSARCH-012
- SYS-033
- SYS-034



#### Traceability




---


### CR-022: Remove DHF-utils and interface items from product DHF (second pass after CR-020)

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Architecture Review  
**Assigned To:** Unassigned

#### Description

CR-020 removed 32 DHF data-layer items from the product DHF. A second pass
removes remaining items that describe DHF utils or interface concerns rather
than CompliantFlow core product features (traceability, compliance, test results).

Removed categories:

1. Item CRUD (DHF utils): UC-001, CRS-001, SYS-001
2. Lifecycle/workflow config (DHF utils): CRS-013, SYS-010
3. Document generation (DHF utils): UC-003, CRS-004, SYS-021
4. Artifact fetcher / test pull (DHF utils): SYS-035, SYSARCH-013
5. CLI interface layer: SYS-032, SRS-012, SWDD-013, SYSARCH-009
6. Verification status display (UI layer): SYS-031, SRS-013, SWDD-015
7. Change request management (DHF workflow): UC-004, CRS-003, SYS-008,
   SYS-030, SRS-006, SRS-007, SWDD-007, SWDD-008, SWDD-017,
   SYSARCH-004, SYSARCH-011

#### Justification

The product DHF documents what CompliantFlow delivers for users as an analysis
and compliance tool: traceability, compliance checking, and test result tracking.
Item CRUD, lifecycle workflows, document generation, change request management,
and CLI interface details are DHF data-layer or interface concerns, documented
in DHF/utils/docs/ or addressed by the underlying tools.

#### Impact Assessment

Deleted from DHF/items/:
  UC-001, UC-003, UC-004
  CRS-001, CRS-003, CRS-004, CRS-013
  SYS-001, SYS-008, SYS-010, SYS-021, SYS-030, SYS-031, SYS-032, SYS-035
  SRS-006, SRS-007, SRS-012, SRS-013
  SWDD-007, SWDD-008, SWDD-013, SWDD-015, SWDD-017
  SYSARCH-004, SYSARCH-009, SYSARCH-011, SYSARCH-013
Updated:
  test_sys_033_test_import.py: re-linked to CRS-008
  test_sys_013_hyperlinks.py: removed stale SRS-013 reference
Deleted tests:
  test_sys_001_object_management.py, test_sys_008_change_management.py
  test_sys_010_lifecycle.py, test_sys_021_document_generation.py
  test_sys_021_pr_cr_automation.py, test_sys_031_test_results.py
  test_sys_032_cli.py, test_crs_001.py, test_crs_003.py

#### Affected Items

- UC-001
- UC-003
- UC-004
- CRS-001
- CRS-003
- CRS-004
- CRS-013
- SYS-001
- SYS-008
- SYS-010
- SYS-021
- SYS-030
- SYS-031
- SYS-032
- SYS-035
- SRS-006
- SRS-007
- SRS-012
- SRS-013
- SWDD-007
- SWDD-008
- SWDD-013
- SWDD-015
- SWDD-017
- SYSARCH-004
- SYSARCH-009
- SYSARCH-011
- SYSARCH-013



#### Traceability




---


### CR-023: ISO 14971 Governance Policy File

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Create a comprehensive governance YAML file for ISO 14971 (Risk Management for Medical Devices) with automated and manual policy checks covering the full risk management lifecycle: hazard identification, risk estimation, risk evaluation, risk control, residual risk evaluation, and risk management review.

#### Justification

ISO 14971 is required for all medical device submissions alongside IEC 62304. Without it, CompliantFlow cannot claim complete DHF coverage and any customer needing risk management traceability (all Class II/III devices) is unserved. Full IEC 62304 + IEC 82304-1 + ISO 14971 coverage is a genuine market differentiator with no competitor match.

#### Impact Assessment

Adding `governance/ISO_14971.yaml` extends the compliance catalog without changing runtime behavior, schemas, or existing item relationships. The change is limited to governance content and enables ISO 14971 policy evaluation to run through the existing compliance engine and CLI/reporting paths.

#### Affected Items

- SYS-005
- CRS-011



#### Traceability




---


### CR-024: Release Gate Enforcement via CLI

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** charles

#### Description

Implement a compliantflow validate release command that evaluates whether a REL item meets all release criteria before permitting a release to proceed. The gate shall check that all linked SYS requirements are verified, all linked CRs are completed, no open DEF items are linked, and compliance scores meet configured thresholds.

#### Justification

IEC 62304 §5.8 requires documented release procedures with objective evidence of readiness. Currently REL items exist in the DHF but are never enforced by the CLI — a release can proceed regardless of open defects or unverified requirements. This is a compliance gap that will be flagged in any serious audit.

#### Impact Assessment

Adds a new validate release subcommand to compliantflow/cli.py and a validate_release() method to CompliantFlowCore. Checks: (1) all CRs in included_items are completed, (2) no open DEF items exist in the DHF, (3) all SYS items have verification_status==verified. Exits 0 if all checks pass, 1 if any fail. No schema or DHF data changes.

#### Affected Items

- SYS-006
- CRS-008



#### Traceability




---


### CR-025: Defect Lifecycle CI Hook

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** charles

#### Description

Integrate DEF item lifecycle into the CI pipeline so that open defects of configured severity levels block merges or fail compliance checks. The system shall scan DHF/items for open DEF items, filter by severity/priority threshold, and surface them as compliance policy failures with links to the DEF item IDs.

#### Justification

IEC 62304 §9.7 and §9.8 require documented defect management with known-anomaly tracking in the release. Currently DEF items exist in the DHF lifecycle but have no CI enforcement — a critical bug can be open while a release proceeds. This is both a compliance gap and a quality risk.

#### Impact Assessment

Adds a new no_open_defects policy check type to compliantflow/policy.py and two IEC 62304 §5.8 governance policies. No schema changes to existing DHF item types. DEF items with open/in_progress status and Critical or High severity will cause compliance checks to fail. Existing DEF-001 (draft) is unaffected by the severity threshold. CI enforcement is implicit through Phase 4 DHF Validation.

#### Affected Items

- SYS-005
- SYS-006
- CRS-008



#### Traceability




---


### CR-026: Innolitics RDM Migration Tooling

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** charles

#### Description

Implement a compliantflow migrate rdm command that converts an Innolitics RDM repository (requirements in YAML/JSON with reST documents) into a CompliantFlow DHF structure. The migration shall map RDM requirement types to CompliantFlow doc types, preserve traceability links, convert document content to Markdown, and produce a migration report summarising items created, skipped, and requiring manual review.

#### Justification

Innolitics RDM is the most widely used open-source medical device requirements tool (~500 GitHub stars) and is effectively unmaintained. Its user base represents the highest-quality near-term acquisition target: teams already doing docs-as-code compliance, pre-qualified for the CLI workflow, and actively looking for a supported alternative. Migration tooling eliminates the main switching cost. This window is time-bounded — another tool will ship migration support eventually.

#### Impact Assessment

Adds compliantflow/migrate/rdm.py (RDMMigrator class) and a new `migrate rdm` CLI command group. No changes to existing DHF schema, policy engine, or CI pipeline. Migration is opt-in and writes only to DHF/items/. No new runtime dependencies — RDM YAML is parsed directly with PyYAML.

#### Affected Items

- SYS-006
- CRS-008



#### Traceability




---


### CR-027: FDA 21 CFR Part 11 Technical Brief

**Status:** COMPLETED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Claude

#### Description

Author a technical brief (document, not code) explaining how CompliantFlow satisfies or addresses FDA 21 CFR Part 11 electronic records and electronic signature requirements. The brief shall cover: Git commit authorship as audit trail, branch protection as access control equivalent, GPG signing as signature mechanism, and known gaps with recommended mitigations for strict Part 11 environments.

#### Justification

US-market SaMD companies under FDA jurisdiction require Part 11 compliance for electronic records. Git author attribution satisfies many Part 11 requirements but auditors unfamiliar with GitOps workflows will raise objections. A written technical brief reviewed by a regulatory consultant eliminates this objection at scale and is the single highest-leverage document CompliantFlow can produce for US market credibility. Cost is one regulatory consultant engagement.

#### Impact Assessment

Adding DHF/documents/technical_briefs/fda_21_cfr_part_11_brief.md — a documentation-only change with no impact on code, schemas, or item relationships. Enables sales and pre-market submission reviewers to understand how CompliantFlow's GitOps architecture satisfies FDA 21 CFR Part 11 electronic records requirements.

#### Affected Items

- CRS-011



#### Traceability




---


### CR-028: GitLab CI and Jenkins Artifact Integration

**Status:** COMPLETED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Claude

#### Description

Extend the test pull command and CI artifact fetcher to support GitLab CI pipelines (via GitLab API and GITLAB_TOKEN) and Jenkins (via Jenkins API and JENKINS_TOKEN). Each integration shall fetch JUnit XML artifacts by job name and run ID, matching the existing GitHub Actions interface.

#### Justification

GitHub Actions is dominant in SaMD startups but a significant portion of medtech companies (especially established device manufacturers and defence-adjacent teams) run GitLab CI or Jenkins. Limiting artifact integration to GitHub Actions blocks these customers from using the automated test import workflow, which is a core value proposition of the platform.

#### Impact Assessment

Adds GitLabArtifactFetcher and JenkinsArtifactFetcher classes to DHF/utils/artifact_fetcher.py, each matching the GitHubArtifactFetcher interface (fetch by run_id or commit SHA, return List[ExecutionResult]). The test pull CLI command gains a --provider flag (github|gitlab|jenkins, default: github) and reads new env vars GITLAB_TOKEN / GITLAB_URL and JENKINS_TOKEN / JENKINS_URL. SYS-007 is updated to reflect the expanded multi-platform scope. CRS-008 already enumerates GitLab CI and Jenkins so no update needed there. No schema changes, no DHFAdapter changes, no compliance policy changes. Risk: low — new code paths; existing GitHub path is unchanged.

#### Affected Items

- SYS-007
- CRS-008



#### Traceability




---


### CR-029: Multi-DHF and Multi-Project Support

**Status:** PLANNED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Enable CompliantFlowCore to operate across multiple DHF directories within a single analysis session, supporting portfolio companies managing multiple medical device products in one repository or across sibling repositories. The implementation shall extend the DHFAdapter protocol to support a router or list of adapters, with cross-project traceability queries scoped appropriately.

#### Justification

Portfolio medical device companies (e.g. a company with two Class II products) currently need separate CompliantFlow deployments per product. Multi-DHF support is a prerequisite for enterprise pricing and for sales to larger organisations that cannot justify per-product licensing. It also unblocks the RBAC milestone in v3.0.0.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-008
- CRS-002



#### Traceability




---


### CR-030: Read-Only Compliance Status Web Dashboard

**Status:** PLANNED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Implement a lightweight read-only web dashboard that displays the current compliance status, traceability matrix, and test result summary for a DHF. The dashboard shall be a single-page application served locally (not cloud-hosted), reading directly from the DHF via the existing DHFAdapter, with no write operations. Target personas: QA and Regulatory Affairs engineers who are not CLI-comfortable.

#### Justification

The CLI-only interface is a barrier for QA/RA personas who need to review compliance status, traceability coverage, and test results but do not work in a terminal. A read-only dashboard extends the product to a second persona within the same team without compromising the CLI-first architecture. This is a deliberate demotion from the original plan: read-only first, full UI later in v3.0.0.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- UC-002
- UC-005
- CRS-002
- CRS-011



#### Traceability




---


### CR-031: Ollama Air-Gap Deployment Package

**Status:** PLANNED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Produce a documented, tested, docker-compose-based deployment package for running CompliantFlow with Ollama in an air-gapped environment. The package shall include: Ollama container configuration, a recommended open-source model selection for semantic compliance checks, environment variable documentation, and a validation script that runs a sample compliance check end-to-end without internet access.

#### Justification

Air-gapped environments are common in defence-adjacent medtech, Class III implantable device teams, and hospital-deployed software. These teams cannot use Gemini API. The OllamaBackend infrastructure exists but there is no deployment guidance, making air-gapped use impractical despite technical feasibility. This CR turns an existing capability into a supported, documented offering.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-009



#### Traceability




---


### CR-032: PDF Submission Template Validation

**Status:** PLANNED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Define and implement validation rules ensuring that CompliantFlow-generated PDF evidence reports conform to regulatory submission templates. The system shall validate report structure, required sections, and content completeness against configurable templates for 510(k), CE marking, and internal QMS submissions. A regulatory consultant review of the generated output shall be incorporated as a manual acceptance criterion.

#### Justification

PDF reports generated by CompliantFlow are intended for regulatory submission as evidence packages. Without format validation, customers risk rejection due to missing sections or non-conformant structure. A validated template eliminates the primary objection from regulatory consultants and submission reviewers unfamiliar with tool-generated evidence.

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SYS-011
- CRS-011



#### Traceability




---


### CR-033: Split RCM implementation_status into two fields

**Status:** PLANNED  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** charles

#### Description

Split the single implementation_status field on RCM items into two separate fields: implementation_status (Planned/Implemented) and verification_status (Not Verified/Verified). This is required so that ISO 14971 policies 7.2.a (controls implemented) and 7.6.b (controls verified) can both be checked simultaneously via attribute_value without conflict. Include a migration script for existing RCM items.

#### Justification

ISO 14971 §7.2 and §7.6 are sequential checks on the same control measure — implementation and subsequent verification of effectiveness. A single status field cannot represent both states simultaneously, causing policy 7.2.a to fail for any RCM that has progressed to Verified. This is a schema blocker for full ISO 14971 automation.

#### Impact Assessment

Schema-only change to DHF/config/doc_types/rcm.yaml: removes Verified from implementation_status options and adds a new verification_status field. Existing RCM items without implementation_status set require no migration. Any RCM with implementation_status=Verified must be updated to implementation_status=Implemented + verification_status=Verified (none exist currently). ISO_14971.yaml policies 7.2.a and 7.6.b updated to use attribute_value checks on the two separate fields. No runtime code changes required.

#### Affected Items

- SYS-005
- SYS-012



#### Traceability




---


### CR-034: Consolidate agent guidance into shared docs/

**Status:** PLANNED  
**Priority:** Low  
**Requested By:** Not Specified  
**Assigned To:** charles

#### Description

Move shared agent/harness guidance out of CLAUDE.md and AGENTS.md into two new canonical files — docs/agent_environment.md and docs/agent_workflow.md. Slim CLAUDE.md and AGENTS.md down to thin entrypoints that reference the shared docs. Update README.md to reflect the new structure.

#### Justification

Agent guidance was duplicated across CLAUDE.md and AGENTS.md, causing drift and maintenance overhead. A single source of truth in docs/ ensures all agent harnesses read the same environment and workflow instructions.

#### Impact Assessment

Documentation-only change. No DHF schema, policy, or runtime code affected. CLAUDE.md and AGENTS.md retain their harness-specific sections; shared content moves to docs/agent_environment.md and docs/agent_workflow.md.

#### Affected Items

- SYS-006



#### Traceability




---


### CRS-002: Complete Traceability

**Status:** UNKNOWN  
**Priority:** Critical  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.




#### Traceability




---


### CRS-008: CI/CD Integration and Automated Test Result Import

**Status:** UNKNOWN  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.




#### Traceability




---


### CRS-011: Regulatory Compliance Validation

**Status:** UNKNOWN  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.




#### Traceability




---


## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | | | |
| Reviewer | | | |
| Approver | | | |

---

*End of Change Request Specification*