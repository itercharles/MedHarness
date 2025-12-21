# System Requirement Specification

<div class="doc-info">

**Document ID**: SYS-SPEC  
**Version**: 1.0  
**Generated**: 2025-12-21  
**Status**: Draft  
**Project**: CompliantFlow Project

</div>

---

## 1. Introduction

This document specifies the System Requirement for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all System Requirements, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all System Requirements defined in the CompliantFlow system as of 2025-12-21.

---

## 2. Requirements

### 1. SYS-001: Parse Specifications

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall ingest specification items defined in YAML files from a structured directory layout.

#### Linked Items

- CRS-002


</div>

### 2. SYS-002: Graph Generation

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall build an in-memory directed graph representing the dependencies between items.

#### Linked Items

- CRS-001


</div>

### 3. SYS-003: Visual Traceability

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall provide a graphical visualization of the traceability graph, including item status.

#### Linked Items

- CRS-001


</div>

### 4. SYS-004: Orphan Reporting

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall display a list of orphan items in the user interface.

#### Linked Items

- RCM-001


</div>

### 5. SYS-005: Governance Definitions

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall parse governance documents (Regulations, Procedures) defined in YAML.

#### Linked Items

- CRS-003


</div>

### 6. SYS-006: Compliance Engine

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall execute automated checks (e.g. coverage, existence) defined in policies.

#### Linked Items

- CRS-003


</div>

### 7. SYS-007: Compliance Reporting

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall evaluate and report the pass/fail status of policies.

#### Linked Items

- CRS-003


</div>

### 8. SYS-008: Change Management System

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  
**Reviewer**: Technical Lead  **Review Date**: 2025-12-13  **Category**: Change Control  **Verification Method**: Inspection and Testing  
#### Description

The system shall provide a change management module that enables tracking, 
evaluation, and approval of changes to medical device software per IEC 62304 §6.2.

The module shall support:
- Creation of change requests with auto-generated IDs
- Impact analysis using the traceability graph
- Workflow-based approval process
- Significance assessment per MDCG 2020-3 criteria
- Change history tracking and reporting

#### Linked Items

- CRS-004


</div>

### 9. SYS-009: Defect Data Capture

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall capture defect information including unique ID, title, description, severity level, reporter, affected items, and reproduction steps.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 10. SYS-010: Defect Workflow Management

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall manage defect lifecycle through defined states (open, investigating, resolved, verified, closed) with controlled state transitions.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 11. SYS-011: Defect Root Cause Documentation

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall require documentation of root cause analysis and resolution details before a defect can be marked as resolved.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 12. SYS-012: Defect Resolution Verification

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall require verification and documentation that the defect resolution is effective before the defect can be closed.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 13. SYS-013: Defect Traceability Links

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall link defects to affected requirements, tests, and optionally to change requests for full traceability.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 14. SYS-014: Defect Change History

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall maintain a complete audit trail of all defect changes including who made changes and when.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 15. SYS-015: Defect Filtering and Reporting

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall provide filtering of defects by status, severity, and assignee, and export defect data for compliance reporting.

#### Linked Items

- CRS-005

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 16. SYS-016: Release Data Capture

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall capture release information including version number, release date, included change requests, test results, defect status, manual verifications with approver identity, and stage approvals with timestamps.

#### Linked Items

- CRS-006

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 17. SYS-017: Release Verification Checks

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall verify that all requirements in a release have passing tests before the release can be approved. Verification shall use configurable workflow criteria including automated checks and manual verification requirements.

#### Linked Items

- CRS-006

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 18. SYS-018: Release Status Workflow

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall manage release lifecycle through states (planning, developing, testing, released) with approval required for each stage transition. Each transition shall enforce configurable criteria before allowing progression.

#### Linked Items

- CRS-006

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 19. SYS-019: Release Documentation Generation

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall generate release documentation including traceability matrix, test summary, and defect report.

#### Linked Items

- CRS-006

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 20. SYS-020: Release History Tracking

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

The system shall maintain a complete history of all releases with version control integration.

#### Linked Items

- CRS-006

#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 21. SYS-021: Document Generation and Export

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Reviewer**: System Architect  **Review Date**: 2024-12-15  **Category**: Document Management  **Verification Method**: Test  
#### Description

The system shall provide document generation capabilities to export CompliantFlow data as regulatory-ready PDF documents.

**Requirements**:
- Generate requirements specification PDFs for CRS, SYS, and SDS
- Generate traceability matrix showing requirement chains and coverage
- Generate release documentation packages
- Use configurable Jinja2 templates for document structure
- Apply professional CSS styling to PDFs
- Provide export functionality through UI

**Acceptance Criteria**:
- PDF documents are generated in < 5 seconds
- Documents include all item data (title, content, status, links)
- Traceability matrix shows coverage percentages
- PDFs are formatted professionally for regulatory submission

#### Linked Items

- CRS-008


</div>

### 22. SYS-022: SOUP Management

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Reviewer**: System Architect  **Review Date**: 2024-12-15  
#### Description

The system shall provide comprehensive management of Software of Unknown Provenance (SOUP) 
to meet IEC 62304 Section 5.3 requirements. This includes:

- Import SOUP items from external scanning tools (Veracode, Snyk, OWASP Dependency-Check)
- Track SOUP metadata (name, version, manufacturer, license, CVE count, risk rating)
- Document SOUP usage purpose and safety classification
- Establish traceability from SOUP to system requirements
- Manage SOUP approval workflow with verification criteria
- Generate SOUP list documentation for regulatory submission

This capability ensures compliance with IEC 62304 requirements for identifying, 
documenting, and managing third-party software components.

#### Linked Items

- CRS-007


</div>

### 23. SYS-023: Configuration-Driven Status Warning Logic

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall determine warning display based on lifecycle configuration's is_stable flag, with fail-fast validation for missing configuration.

#### Linked Items

- CRS-009


</div>

### 24. SYS-024: Automatic Verification Column Detection

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall automatically add a verification status column when the last item in a trace path contains a verification_status field.

#### Linked Items

- CRS-010


</div>

### 25. SYS-025: Policy Group Loading and Selection

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall load policy groups from the governance directory and allow users to select a specific policy group for validation.

#### Linked Items

- CRS-011


</div>

### 26. SYS-026: Compliance Score Calculation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall calculate an overall compliance score as a percentage of passed policies and display it with color-coded indicators (green >= 90%, yellow >= 70%, red < 70%).

#### Linked Items

- CRS-011


</div>

### 27. SYS-027: Policy Validation Results Display

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall display validation results for each policy with pass/fail status, policy description, and detailed evidence in an expandable format.

#### Linked Items

- CRS-011


</div>

### 28. SYS-028: Dynamic Page Registration

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall read doc_types from project configuration, filter for page_enabled=true, and dynamically register Streamlit pages at application startup.

#### Linked Items

- CRS-012


</div>

### 29. SYS-029: Unique Page URL Generation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall generate unique URL paths for each dynamically created page using page_number and doc_type code to prevent URL conflicts.

#### Linked Items

- CRS-012


</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 29 |
| **Approved** | 10 |
| **Draft** | 19 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 34.5% (10/29)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2025-12-21  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
