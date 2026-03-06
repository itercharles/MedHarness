# System Requirement Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SYS-SPEC |
| **Version** | 1.105 |
| **Generated** | 2026-03-06 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the System Requirement for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all System Requirements, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all System Requirements defined in the CompliantFlow system as of 2026-03-06.

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
- cr check-status / update: Verify CR state; add affected items and PR metadata
- traceability matrix / chain: Output traceability matrix or full item chain as JSON
- test import / status / list: Import JUnit XML results; query stored TC records
- doc list / generate / export: List configured doc types; generate markdown; export PDF



</div>

### 11. SYS-033: External Test Result Integration via CLI

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  
**Category**: Functional  **Verification Method**: ['Test']  
#### Description

The system shall provide CLI commands that allow CI/CD pipelines to push
test execution results and test case design-review metadata into the DHF,
independent of the test framework or programming language used.

Required commands:
- test import: Parse a JUnit XML file produced by any test framework and persist
  per-TC execution results (tester, testing date, testing status, run ID, run URL,
  commit SHA, notes) and optional review metadata (reviewer, review date, review status)
  from JUnit XML properties.  Automatically updates verification_status on linked
  requirement items (verified / failed / not_verified).
- test status: Retrieve the stored record for a single TC as JSON.
- test list: List all stored TC records, optionally filtered by testing_status.

Results are persisted in DHF/test-results/results.yaml.



</div>

### 12. SYSARCH-001: Item Management Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Core module for managing DHF items (requirements, design, tests, change requests, etc.).

**Responsibilities**:
- Load items from YAML files with schema validation
- Save items with Git commit tracking
- Support configurable item types from project configuration
- Maintain item history and audit trail

**Key Interfaces**:
- `ItemLoader`: Load items from file system by ID, type, or all items
- `ItemSaver`: Save items with validation and Git commits
- `ItemValidator`: Validate item schema against configuration

**Implementation Notes**:
- Uses YAML format for human-readable storage
- Git integration provides automatic version control
- Pydantic models for type-safe item validation
- File-based storage enables simple backup and portability



</div>

### 13. SYSARCH-002: Traceability Analysis Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for building and analyzing traceability relationships between DHF items.

**Responsibilities**:
- Build directed graph from item links
- Find upstream/downstream dependencies
- Detect orphan items (no incoming or outgoing links)
- Calculate coverage metrics (requirements to tests)
- Support configurable traceability paths from configuration

**Key Interfaces**:
- `GraphBuilder`: Construct traceability graph from all items
- `TraceabilityAnalyzer`: Analyze relationships and dependencies
- `OrphanDetector`: Find items without required links
- `CoverageCalculator`: Compute verification coverage

**Implementation Notes**:
- Uses NetworkX library for graph operations
- In-memory graph for fast queries
- Supports bidirectional traversal
- Configurable relationship types (derives_from, implements, verifies)



</div>

### 14. SYSARCH-003: Lifecycle Management Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for managing item lifecycle states and transitions via CompliantFlowCore.

**Scope**: Explicit lifecycle applies ONLY to CR, REL, and DEF. Requirement items
(UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM) use the GitOps approval model
— no status field, no transitions. See SWDD-016 for the GitOps approval design.

**Responsibilities**:
- Load lifecycle configuration from project config
- Validate state transitions against strict rules (CR/REL/DEF only)
- Execute transition criteria checks (field validation, manual approval)
- Enforce approval workflows for CR/REL/DEF
- Support configurable lifecycles per document type

**Key Interfaces**:
- `CompliantFlowCore`: Main entry point for lifecycle operations
- `LifecycleMethods`: Internal logic for state validation
- `TransitionValidator`: Check if transition is allowed
- `CriteriaExecutor`: Execute validation criteria

**Implementation Notes**:
- Configuration-driven (no hardcoded workflows)
- Requirement items have no lifecycle config entry → get_initial_state() returns None,
  get_available_transitions() returns []
- Extensible criteria system (field checks, manual verification, linked item status)
- Strict validation with clear error messages (Fail-Fast)



</div>

### 15. SYSARCH-004: Change Management Module

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

### 16. SYSARCH-005: Compliance Validation Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for validating DHF against regulatory policies and standards.

**Responsibilities**:
- Load policy definitions from configuration files
- Execute validation rules against DHF items
- Calculate compliance scores per policy group
- Display validation results with detailed evidence
- Support custom policy definitions

**Key Interfaces**:
- `PolicyEngine`: Load and execute validation rules
- `ComplianceScorer`: Calculate compliance percentages
- `EvidenceCollector`: Gather validation evidence and details
- `PolicyValidator`: Validate policy configuration

**Implementation Notes**:
- Policy-based architecture for flexibility
- Supports multiple policy groups (IEC 62304, FDA 21 CFR 820, etc.)
- Extensible validation rule types (coverage, orphan, status checks)
- Clear pass/fail results with actionable recommendations



</div>

### 17. SYSARCH-006: Document Generation Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for generating regulatory specification documents from templates.

**Responsibilities**:
- Render Jinja2 templates with item data
- Generate specification documents (requirements, architecture, tests)
- Export documents to PDF format
- Track document versions and generation history
- Support configurable document templates

**Key Interfaces**:
- `TemplateRenderer`: Render Jinja2 templates with context data
- `PDFExporter`: Convert markdown to PDF using WeasyPrint
- `DocumentVersioner`: Track and increment document versions
- `TemplateManager`: Load and validate templates

**Implementation Notes**:
- Uses Jinja2 for flexible templating
- WeasyPrint for professional PDF generation
- Automatic version incrementing from existing documents
- Templates stored in version control for auditability



</div>

### 18. SYSARCH-007: Test Integration Module

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Module for importing and persisting test results from any CI/CD pipeline
into the DHF, and linking each result to the requirement items it verifies.

**Framework-agnostic boundary**:
- `src/` consumes only JUnit XML — no coupling to any specific test framework
- `tests/` contains the pytest-specific adapter (conftest.py + docstring_parser.py)
- Any framework that produces JUnit XML with `compliantflow.*` properties is compatible

**Responsibilities**:
- Parse JUnit XML produced by any test framework
- Extract TC IDs from `compliantflow.id` property or test name regex
- Extract review metadata from `compliantflow.reviewer`, `.review_date`, `.review_status`
- Persist results to `DHF/test-results/results.yaml`
- Recompute `verification_status` on linked requirement items after import

**Key Interfaces**:
- `parse_junit_xml(path)` — parse JUnit XML into `ExecutionResult` list
- `ResultStore.record_execution(...)` — upsert one TC record in results.yaml
- `_TestResultsMixin.import_test_results(...)` — orchestrate import and
  verification_status update on linked items
- CLI: `compliantflow test import <file> --format junit`

**Implementation Notes**:
- TC ID extracted from `compliantflow.id` property, or by regex from test name
- Git history of `results.yaml` serves as the audit trail
- For pytest projects: `tests/conftest.py` autouse fixture injects
  `compliantflow.*` properties from docstring `@`-tags automatically
- `tests/utils/docstring_parser.py` provides shared helpers for tag extraction



</div>

### 19. SYSARCH-008: Web UI Module

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

### 20. SYSARCH-009: CLI Module

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

### 21. SYSARCH-010: GitOps-Based Approval Architecture

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Architectural decision: requirement items use Git as the sole approval mechanism
rather than an explicit lifecycle state machine.

**Decision**:
UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, and RCM items carry NO status field
and have NO lifecycle transitions. Only CR, REL, and DEF retain explicit lifecycle
workflows.

**Approval Model**:
- main branch  → item is approved (PR merge = approval evidence)
- feature branch → item is draft / under review
- deleted from repo → item is retired

**Rationale**:
- Eliminates redundant status: approved fields on 65 YAML files
- Prevents stale approval metadata when items are edited on branches
- Git PR review (with required reviewers and CI checks) already serves as the
  approval gate — duplicating that as a YAML field adds noise, not value
- Simplifies the data model: requirement items are just content files, not workflow objects
- CR, REL, DEF need explicit states because they have multi-step processes
  (e.g., CR: draft→in_review→approved→implementing→completed) that go beyond
  the binary approved/not-approved signal Git provides

**Implementation**:
- `project_config.yaml`: no `lifecycle` block on requirement doc types
- `create_item()`: does not set status when `get_initial_state()` returns None
- `get_available_transitions()`: returns [] for items with no lifecycle config
- Schema validation: status field is still in _SYSTEM_FIELDS (allowed but not set)
- Design detail: see SWDD-016 (GitOps approval model)



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 21 |
| **Approved** | 0 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 0.0% (0/21)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2026-03-06  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
