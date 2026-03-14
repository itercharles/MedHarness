# System Requirement Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SYS-SPEC |
| **Version** | 1.139 |
| **Generated** | 2026-03-14 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the System Requirement for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all System Requirements, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all System Requirements defined in the CompliantFlow system as of 2026-03-14.

---

## 2. Requirements

### 1. SYS-001: Objects management and tracking

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  
#### Description

The system shall support configurable object, such as requirement, design item, change request, etc. to maintain a complete history.


#### Verification Status

**Status**: PASS

</div>

### 2. SYS-003: Visual Traceability

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  
#### Description

The system shall provide a view of traceability graph or table, including requirements, architecture, tests, and change requests.



</div>

### 3. SYS-004: Orphan Reporting

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  
#### Description

The system shall display a list of orphan items.



</div>

### 4. SYS-005: Compliance Assessment

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  
#### Description

The system shall able to assess the compliance of the DHF by the governance policies (Regulations, Procedures) from configuration files.



</div>

### 5. SYS-008: Change Management System

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Reviewer**: Technical Lead  **Review Date**: 2025-12-13  **Category**: Change Control  **Verification Method**: ['Inspection', 'Test']  
#### Description

The system shall provide a change management module that enables tracking, evaluation, and approval of changes.



</div>

### 6. SYS-010: Object Workflow Management

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  
#### Description

The system shall support two complementary approval models:

1. **GitOps Approval Model** (UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM): approval
   state is derived from the Git branch — main branch = approved, feature branch = draft/in-review,
   deleted from repo = retired. No explicit status field is stored on these items.

2. **Configurable Lifecycle Workflows** (CR, REL, DEF): explicit state transitions and validation
   rules defined in configuration. The system shall enforce the configured transition rules,
   including field validation and linked-item status checks.



</div>

### 7. SYS-021: Document Generation and Export

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Reviewer**: System Architect  **Review Date**: 2024-12-15  **Category**: Document Management  **Verification Method**: ['Test']  
#### Description

The system shall provide document generation capabilities to export CompliantFlow data as regulatory-ready PDF documents. Generate requirements specification PDFs for requirements, design, change requests, etc.



</div>

### 8. SYS-030: Automated Change Request Workflow

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  **Verification Method**: ['Test']  
#### Description

The system shall provide automated workflows to link Pull Requests and changed objects to Change Requests, ensuring complete traceability and regulatory compliance.



</div>

### 9. SYS-031: Test Verification Status Display

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  **Verification Method**: ['Test']  
#### Description

The system shall display the verification status (verified / failed / not_verified) of each requirement item in traceability views, showing which requirements are covered by passing test cases and which have failures or no test results.



</div>

### 10. SYS-032: Command-Line Interface

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  **Verification Method**: ['Test']  
#### Description

The system shall provide a command-line interface (CLI) accessible via
`python -m compliantflow` that exposes core DHF operations for use in
CI/CD pipelines and scripted environments.

Required command groups:
- validate schema / traceability / compliance: Validate DHF items; exit non-zero on error
- item list / get / create / update / delete: CRUD operations on DHF items; output JSON
- item transitions / transition: List available transitions and execute a state transition
- cr check-status / update: Verify CR state; add affected items to a CR
- traceability matrix / chain: Output traceability matrix or full item chain as JSON
- test import / status / list: Import JUnit XML results; query stored TC records
- doc list / generate / export: List configured doc types; generate markdown; export PDF



</div>

### 11. SYS-035: On-Demand Test Result Retrieval from CI Artifacts

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Maintainability  **Verification Method**: ['Test', 'Inspection']  
#### Description

The system shall provide a mechanism to retrieve test execution results from
GitHub Actions artifacts on demand, without requiring the CI pipeline to commit
data to the repository.

Acceptance criteria:
1. A CLI command 'test pull' shall fetch JUnit XML artifacts for a specified run
   (or the latest run for the current HEAD commit) from the GitHub Actions API.
2. The command shall require GITHUB_TOKEN to be set in the environment.
3. After 'test pull', verification_status for linked requirement items shall be
   computable from the fetched results within the current session.
4. The CI pipeline shall not commit any data to the repository during test runs.
5. The local result cache (results.yaml) shall not be tracked in git.



</div>

### 12. SYSARCH-004: Change Management Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for tracking and controlling changes to DHF items through change requests.

**Responsibilities**:
- Create and manage change request lifecycle
- Link GitHub Pull Requests to change requests
- Track affected items in change requests
- Enforce change control policies (prevent editing stable items)
- Maintain complete audit trail of changes

**Key Interfaces**:
- `ChangeRequestManager`: CR creation, update, approval
- `ImpactAnalyzer`: Identify items affected by changes
- `PRLinker`: Link GitHub PRs to CRs automatically
- `ChangeControlPolicy`: Enforce editing restrictions

**Implementation Notes**:
- Integrates with GitHub API for PR information
- Automated detection of affected items from PR file changes
- Prevents editing of items in stable status without CR
- Git commits link to change request IDs



</div>

### 13. SYSARCH-008: Web UI Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Streamlit-based web user interface for DHF management.

**Responsibilities**:
- Render item management pages dynamically from configuration
- Display traceability visualizations (graphs, matrices)
- Show compliance dashboards and validation results
- Provide document preview and export
- Support navigation, search, and filtering

**Key Interfaces**:
- `PageGenerator`: Dynamic page creation from configuration
- `UIComponents`: Reusable UI elements (tables, forms, badges)
- `NavigationManager`: Handle routing and query parameters
- `VisualizationRenderer`: Display graphs and charts

**Implementation Notes**:
- Built with Streamlit framework
- Configuration-driven page generation
- Responsive layout with browser compatibility
- Real-time updates via Streamlit's reactive model



</div>

### 14. SYSARCH-009: CLI Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Two CLI modules providing headless access to DHF operations for CI/CD pipelines,
split by the DHF data layer extraction (CR-013).

**compliantflow CLI** (`src/compliantflow/cli.py`, entry: `python -m compliantflow`):
- Analysis and lifecycle operations: traceability validation, compliance checking,
  item lifecycle transitions, CR management, test result import/query,
  traceability matrix and chain views
- Routes to `CompliantFlowCore` for all operations
- No item CRUD (create/update/delete); those are in the dhf CLI

**dhf CLI** (`DHF/utils/cli.py`, entry: `python -m utils`):
- Data-layer operations only: item CRUD, schema validation, config inspection,
  document generation and PDF export
- Routes to `LocalDHFAdapter` — no dependency on the compliantflow analysis package
- Can be used standalone without CompliantFlowCore

**Shared conventions**:
- `click` library for argument parsing and help generation
- DHF path: `--dhf` option → `COMPLIANTFLOW_DHF` env var → `<repo_root>/DHF` default
- stdout = machine-readable JSON; stderr = human-readable diagnostics
- Exit codes: 0 success, 1 business error, 2 usage error
- Stateless: each invocation creates a fresh instance; no shared state with the Web UI



</div>

### 15. SYSARCH-011: PR-to-CR Linkage is GitOps-Implicit, Not YAML-Stored

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Architectural decision: the association between a Pull Request and a Change
Request is captured implicitly by Git conventions, not by writing PR metadata
into CR YAML files.

**Decision**:
CR items do NOT store pr_number, pr_url, or pr_title. The CI pipeline does NOT
write these fields. The implementation_prs property is removed from the CR
schema.

**Linkage conventions (all enforced or auditable)**:
- PR title MUST start with CR-NNN (enforced by CI Phase 4 validation step)
- Branch name convention: feature/cr-NNN-<description>
- Commit messages carry the CR-NNN prefix by convention

Searching GitHub for "CR-017" returns all PRs, commits, and comments associated
with that CR. No separate record in YAML is needed.

**Rationale**:

1. Eliminates stale-data hazard: a PR can be closed, re-opened with a new
   number, or retitled. Any PR metadata stored in YAML at open/synchronize
   time becomes incorrect. There is no reliable event to clean it up.

2. Removes a CI write on feature branches: Phase 4 pushed a bot commit to the
   feature branch on every PR open/synchronize event. This caused race
   conditions with developer commits and re-triggered CI runs.

3. Avoids redundancy: the PR title convention (CR-NNN:) already provides
   machine-readable linkage in GitHub's own index. Writing it again to a YAML
   file duplicates data without adding value.

4. Consistent with SYSARCH-010 (GitOps approval model): that decision
   established Git as the source of truth for approval evidence on requirement
   items. The same principle applies to the PR-CR association — Git history
   already carries the evidence.

**What CI still writes automatically**:
- `affected_items`: items whose YAML files changed in the PR diff. This IS
  stable DHF data (which items are in scope for this CR) and is worth persisting.

**Tradeoff accepted**:
- PR numbers are not directly visible in the CR YAML. Engineers who need to
  cross-reference must search GitHub. This is acceptable because GitHub search
  on the CR-NNN prefix is fast and always accurate.

**Design detail**: see SWDD-017.



</div>

### 16. SYSARCH-013: GitHub Actions Artifacts as Test Result Source of Truth

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Architectural decision: GitHub Actions artifacts are the sole authoritative store
for test execution results. The DHF layer does not maintain a committed replica.

## Rationale

Storing a committed copy of test results (results.yaml) in the git repository
creates a tight coupling between the CI pipeline and the repository state:
- CI must have write access to the branch it is testing.
- Concurrent runs can produce conflicting commits.
- The copy is a derivative of the artifacts with no independent value.

## New Data Flow

```
CI (push or PR trigger)
  ├─ Phase 1: tests/srs/  → unit-test-results.xml (artifact, retained 90 days)
  ├─ Phase 2: tests/sys/  → sys-test-results.xml  (artifact)
  └─ Phase 3: tests/crs/  → crs-test-results.xml  (artifact)
  [no further CI steps that write to the repo]

On-demand access
  └─ compliantflow test pull [--run-id RUN_ID]
      └─ GitHubArtifactFetcher (DHF/utils/artifact_fetcher.py)
          ├─ GET /repos/{repo}/actions/runs/{id}/artifacts
          ├─ Download artifact ZIPs, extract XML
          └─ parse_junit_xml() → ExecutionResult list → local ResultStore cache
```

## Layer Responsibilities

| Layer | Responsibility |
|---|---|
| GitHub Actions | Execute tests, upload JUnit XML artifacts |
| DHF/utils/artifact_fetcher.py | GitHub API auth, run lookup, artifact download |
| DHF/utils/result_store.py | Local cache (git-ignored results.yaml) |
| LocalDHFAdapter | Bridges DHF fetcher to DHFAdapter protocol |
| CompliantFlowCore | Calls adapter.pull_results_from_artifacts(); knows nothing of GitHub |
| CLI (test pull) | User-facing trigger; exits 1 if any TC FAILed |

## Verification Status

After 'test pull', verification_status on requirement items is computed in-memory
and injected into the graph. Requirement YAML files are NOT modified — the GitHub
Actions run URL + commit SHA in each result record serve as the regulatory audit trail.

## Audit Retention

Default GitHub artifact retention is 90 days. Adjust via repository Settings →
Actions → Artifact and log retention for longer-term compliance requirements.



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 16 |
| **Approved** | 0 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 0.0% (0/16)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2026-03-14  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
