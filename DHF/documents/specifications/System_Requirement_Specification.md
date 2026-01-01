# System Requirement Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SYS-SPEC |
| **Version** | 1.69 |
| **Generated** | 2025-12-28 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the System Requirement for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all System Requirements, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all System Requirements defined in the CompliantFlow system as of 2025-12-28.

---

## 2. Requirements

### 1. SYS-001: Objects management and tracking

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable object, such as requirement, design item, change request, etc. to maintain a complete history.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 2. SYS-003: Visual Traceability

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall provide a view of traceability graph or table, including requirements, architecture, tests, and change requests.



</div>

### 3. SYS-004: Orphan Reporting

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall display a list of orphan items.



</div>

### 4. SYS-005: Compliance Assessment

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall able to assess the compliance of the DHF by the governance policies (Regulations, Procedures) from configuration files.



</div>

### 5. SYS-008: Change Management System

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Reviewer**: Technical Lead  **Review Date**: 2025-12-13  **Category**: Change Control  **Verification Method**: Inspection and Testing  
#### Description

The system shall provide a change management module that enables tracking, evaluation, and approval of changes.



</div>

### 6. SYS-010: Object Workflow Management

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable lifecycle workflows for objects (such as requirements, design items, change requests), with state transitions and validation rules defined in configuration. The system shall enforce the custom transition rules.



</div>

### 7. SYS-021: Document Generation and Export

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Reviewer**: System Architect  **Review Date**: 2024-12-15  **Category**: Document Management  **Verification Method**: Test  
#### Description

The system shall provide document generation capabilities to export CompliantFlow data as regulatory-ready PDF documents. Generate requirements specification PDFs for requirements, design, change requests, etc.



</div>

### 8. SYS-030: Automated Change Request Workflow

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Category**: functional  **Verification Method**: Test  
#### Description

The system shall provide automated workflows to link Pull Requests and changed objects to Change Requests, ensuring complete traceability and regulatory compliance.



</div>

### 9. SYS-031: Test result retrive and display

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Category**: functional  **Verification Method**: Test  
#### Description

The system shall retrive the test result from pipeline and display it in the system.



</div>

### 10. SYSARCH-001: Item Management Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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

### 11. SYSARCH-002: Traceability Analysis Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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

### 12. SYSARCH-003: Lifecycle Management Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Module for managing item lifecycle states and transitions via CompliantFlowCore.

**Responsibilities**:
- Load lifecycle configuration from project config
- Validate state transitions against strict rules
- Execute transition criteria checks (field validation, manual approval)
- Enforce approval workflows
- Support configurable lifecycles per item type

**Key Interfaces**:
- `CompliantFlowCore`: Main entry point for lifecycle operations
- `LifecycleMethods`: Internal logic for state validation
- `TransitionValidator`: Check if transition is allowed
- `CriteriaExecutor`: Execute validation criteria

**Implementation Notes**:
- Configuration-driven (no hardcoded workflows)
- Supports multiple lifecycle models per document type
- Extensible criteria system (field checks, manual verification, linked item status)
- Strict validation with clear error messages (Fail-Fast)



</div>

### 13. SYSARCH-004: Change Management Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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

### 14. SYSARCH-005: Compliance Validation Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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

### 15. SYSARCH-006: Document Generation Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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

### 16. SYSARCH-007: Test Integration Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Module for retrieving and displaying test results from CI/CD pipeline.

**Responsibilities**:
- Fetch test results from GitHub Actions workflows
- Parse test result artifacts (JUnit XML, pytest reports)
- Display pass/fail status in UI
- Link test results to requirement items
- Track test execution history

**Key Interfaces**:
- `TestResultFetcher`: Retrieve results from GitHub API
- `TestResultParser`: Parse various test result formats
- `TestStatusDisplay`: Show results in UI with details
- `TestLinkManager`: Link tests to requirements

**Implementation Notes**:
- Integrates with GitHub Actions API
- Supports multiple test result formats
- Caches test results for performance
- Provides drill-down to test execution logs



</div>

### 17. SYSARCH-008: Web UI Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

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


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 17 |
| **Approved** | 17 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 100.0% (17/17)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2025-12-28  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
