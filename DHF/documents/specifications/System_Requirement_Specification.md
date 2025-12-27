# System Requirement Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SYS-SPEC |
| **Version** | 1.53 |
| **Generated** | 2025-12-27 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the System Requirement for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all System Requirements, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all System Requirements defined in the CompliantFlow system as of 2025-12-27.

---

## 2. Requirements

### 1. SYS-001: Parse Specifications

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Category**: functional  **Verification Method**: Test  
#### Description

The system shall ingest specification items defined in YAML files from a structured directory layout.



</div>

### 2. SYS-002: Graph Generation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall build a directed graph data structure to represent traceability relationships between items. (Test: GitHub Actions automation)



</div>

### 3. SYS-003: Visual Traceability

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall provide a graphical visualization of the traceability graph, including item status.



</div>

### 4. SYS-004: Orphan Reporting

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall display a list of orphan items in the user interface.



</div>

### 5. SYS-005: Governance Definitions

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall parse governance documents (Regulations, Procedures) defined in YAML.



</div>

### 6. SYS-006: Compliance Engine

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall execute automated checks (e.g. coverage, existence) defined in policies.



</div>

### 7. SYS-007: Compliance Reporting

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall execute policy validation rules defined in configuration and report results. Policy definitions and validation logic shall be configurable.



</div>

### 8. SYS-008: Change Management System

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
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



</div>

### 9. SYS-009: Defect Data Capture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall capture defect information including unique ID, title, description, severity level, reporter, affected items, and reproduction steps.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 10. SYS-010: Defect Workflow Management

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable lifecycle workflows for items, with state transitions and validation rules defined in configuration. The system shall enforce transition rules and execute validation criteria.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 11. SYS-011: Defect Root Cause Documentation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall require documentation of root cause analysis and resolution details before a defect can be marked as resolved.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 12. SYS-012: Defect Resolution Verification

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable verification requirements before state transitions. Required verification fields and criteria shall be defined in configuration and enforced by the system.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 13. SYS-013: Defect Traceability Links

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall link defects to affected requirements, tests, and optionally to change requests for full traceability.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 14. SYS-014: Defect Change History

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall maintain a complete audit trail of all defect changes including who made changes and when.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 15. SYS-015: Defect Filtering and Reporting

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall provide filtering of defects by status, severity, and assignee, and export defect data for compliance reporting.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 16. SYS-016: Release Data Capture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable data fields for items. Field definitions, types, validation rules, and required fields shall be defined in configuration.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 17. SYS-017: Release Verification Checks

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall execute configurable verification checks before state transitions. Verification rules and criteria shall be defined in configuration and enforced by the system.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 18. SYS-018: Release Status Workflow

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall support configurable lifecycle workflows with approval gates. Transition criteria and approval requirements shall be defined in configuration and enforced by the system.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 19. SYS-019: Release Documentation Generation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall generate release documentation including traceability matrix, test summary, and defect report.


#### Verification Status

**Status**: VerificationStatus.PASS

</div>

### 20. SYS-020: Release History Tracking

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall maintain a complete history of all releases with version control integration.


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



</div>

### 23. SYS-023: Configuration-Driven Status Warning Logic

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall determine warning display based on lifecycle configuration's is_stable flag, with fail-fast validation for missing configuration.



</div>

### 24. SYS-024: Automatic Verification Column Detection

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall automatically add a verification status column when the last item in a trace path contains a verification_status field.



</div>

### 25. SYS-025: Policy Group Loading and Selection

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall load policy groups from the governance directory and allow users to select a specific policy group for validation.



</div>

### 26. SYS-026: Compliance Score Calculation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall calculate an overall compliance score as a percentage of passed policies and display it with color-coded indicators (green >= 90%, yellow >= 70%, red < 70%).



</div>

### 27. SYS-027: Policy Validation Results Display

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall display validation results for each policy with pass/fail status, policy description, and detailed evidence in an expandable format.



</div>

### 28. SYS-028: Dynamic Page Registration

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall read doc_types from project configuration, filter for page_enabled=true, and dynamically register Streamlit pages at application startup.



</div>

### 29. SYS-029: Unique Page URL Generation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall generate unique URL paths for each dynamically created page using page_number and doc_type code to prevent URL conflicts.



</div>

### 30. SYS-030: Automated Change Request Workflow

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  
**Category**: functional  **Verification Method**: Test  
#### Description

The system shall provide automated workflows to link Pull Requests to Change Requests, 
ensuring complete traceability and regulatory compliance.

**Rationale**: This requirement supports IEC 62304 §6.2 (Change Control) and FDA 21 CFR 820.30(i) 
(Design Change Documentation) by automating the linkage between code changes and change requests.




</div>

### 31. SYSARCH-001: Web-Based Application Architecture

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

System architecture decisions:

**Deployment Model:**
- Web-based Python application
- Browser-based user interface
- Local or server deployment
- No database server required

**Technology Choices:**
- Python 3.11+ runtime
- Streamlit web framework
- File-based data storage
- Git version control

**Rationale:**
- Simple deployment (no complex infrastructure)
- Familiar web interface
- Portable (entire DHF is a directory)
- Standards-compliant audit trail via Git



</div>

### 32. SYSARCH-002: File-Based Data Storage Architecture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Data storage approach:

**Storage Medium:**
- YAML files for structured data
- Markdown files for generated documents
- Git repository for version control

**Directory Structure:**
- Organized by document type
- One file per item
- Human-readable format

**Benefits:**
- No database setup required
- Easy to backup (copy directory)
- Git-friendly (text-based)
- Transparent (inspect with any editor)
- Regulatory-friendly (easy to archive)

**Trade-offs:**
- Not suitable for >1000s of items
- Limited concurrent editing
- No complex queries



</div>

### 33. SYSARCH-003: Traceability Graph Architecture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Graph-based traceability architecture:

**Graph Technology:**
- NetworkX directed graph library
- Nodes represent DHF items
- Edges represent traceability relationships

**Graph Structure:**
- Node attributes: item ID, type, title, status
- Edge attributes: relationship type (derives_from, implements, verifies)
- Bidirectional traversal support

**Traceability Operations:**
- Build graph from all items at startup
- Find upstream items (parents)
- Find downstream items (children)
- Detect orphans (no incoming/outgoing edges)
- Calculate coverage (source to verification)

**Visualization:**
- Interactive graph display
- Color-coded by status
- Shape-coded by type
- Clickable nodes for navigation

**Rationale:**
- NetworkX provides mature graph algorithms
- In-memory graph for fast queries
- Supports complex traceability analysis
- Standard Python library (well-documented)



</div>

### 34. SYSARCH-004: Configuration-Driven Workflow Architecture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

YAML-based configuration architecture for workflows:

**Configuration Source:**
- project_config.yaml as single source of truth
- Pydantic models for schema validation
- Fail-fast on invalid configuration

**Lifecycle Configuration:**
- States: id, label, color, icon, is_stable, is_initial
- Transitions: from, to, label, validation_criteria
- Per-document-type lifecycle definitions

**Workflow Engine:**
- Load lifecycle from configuration at startup
- Validate state transitions against rules
- Execute validation criteria before transitions
- Support approval workflows

**Status Warning Logic:**
- Use is_stable flag to determine warnings
- Show ⚠️ for items not in stable states
- Configuration-driven (no hardcoded states)

**Verification Column Detection:**
- Automatic detection based on field presence
- Configurable verification status display
- Support for automated and manual verification

**Rationale:**
- Configuration-driven = no code changes for new workflows
- YAML = human-readable and version-controllable
- Pydantic = strong typing and validation
- Fail-fast = catch errors early



</div>

### 35. SYSARCH-005: Policy-Based Compliance Architecture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Configurable policy engine architecture:

**Policy Configuration:**
- Policy groups defined in configuration
- Each policy has name, description, applicable types
- Validation rules defined per policy

**Policy Engine:**
- Load policies from configuration
- Execute validation rules against items
- Collect pass/fail results
- Calculate compliance scores

**Validation Rule Types:**
- Coverage rules: Check source items have verification
- Orphan rules: Check items have required parents
- Status rules: Check items in required states
- Custom rules: Extensible validation framework

**Scoring Algorithm:**
- Each rule has equal weight (configurable)
- Score = (passed_rules / total_rules) * 100
- Detailed results with evidence

**Results Display:**
- Expandable sections per policy
- Pass/fail indicators
- Detailed evidence for failures
- Actionable recommendations

**Rationale:**
- Policy-based = flexible compliance checking
- Configuration-driven = no code for new policies
- Extensible = support custom validation logic
- Transparent = clear audit trail



</div>

### 36. SYSARCH-006: Document Generation and History Architecture

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Template-based document generation with Git history:

**Template Engine:**
- Jinja2 for template rendering
- Templates stored in version control
- Support for multiple output formats

**Generation Process:**
- Load template from configured directory
- Gather item data for context
- Render template with Jinja2
- Apply format conversion (if needed)
- Include metadata (version, date, status)

**History Tracking:**
- Git commits for all item changes
- Commit messages include item ID and action
- Author attribution from user context
- Full audit trail via Git log

**Change History Display:**
- Parse Git log for item files
- Show timeline of changes
- Display author and timestamp
- Support diff between versions

**Documentation Generation:**
- Automated specification documents
- Traceability matrices
- Compliance reports
- Release notes

**Rationale:**
- Jinja2 = industry-standard templating
- Git = built-in version control and audit trail
- Template-based = easy to customize documents
- Automated = reduce manual documentation effort



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 36 |
| **Approved** | 34 |
| **Draft** | 2 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 94.4% (34/36)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2025-12-27  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
