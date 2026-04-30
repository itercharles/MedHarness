# Software Requirement Specification Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SRS-SPEC |
| **Version** | 1.2 |
| **Generated** | 2026-03-03 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the Software Requirement Specification for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all Software Requirement Specifications, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all Software Requirement Specifications defined in the CompliantFlow system as of 2026-03-03.

---

## 2. Requirements

### 1. SRS-001: Item Persistence and Versioning

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall persist DHF items to file storage with complete version history.

Behavior:
- Store each item as separate file with unique identifier
- Automatically generate unique IDs in format {PREFIX}-{NUMBER} (e.g., SRS-001)
- Use sequential numbering based on existing items (max + 1)
- Prevent duplicate IDs by checking existing items before creation
- Maintain complete change history with author and timestamp
- Support atomic read and write operations
- Validate item schema before persistence

Acceptance Criteria:
- Items can be saved and retrieved by ID
- IDs are automatically generated and unique
- Change history includes author, timestamp, and changes made
- Invalid items are rejected with clear error messages
- Concurrent access does not corrupt data



</div>

### 2. SRS-002: Traceability Graph Construction

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall build directed graph representing traceability relationships between items.

Behavior:
- Create graph nodes for each DHF item
- Create graph edges from item link fields
- Support bidirectional traversal (upstream and downstream)
- Update graph when items are added, modified, or deleted

Acceptance Criteria:
- Graph contains all items as nodes
- Edges correctly represent configured relationship types
- Can find all parent items (upstream traversal)
- Can find all child items (downstream traversal)
- Graph updates reflect item changes within 1 second



</div>

### 3. SRS-003: Orphan Item Detection

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall identify items that lack required traceability links.

Behavior:
- Detect items with no incoming links (missing parents)
- Detect items with no outgoing links (missing children)
- Exclude configured root types from orphan detection
- Group orphans by document type

Acceptance Criteria:
- Orphan detection completes in < 1 second for 1000 items
- Root types (UC, CRS) are not flagged as orphans
- Orphans are correctly grouped by document type
- Detection updates when items are linked/unlinked



</div>

### 4. SRS-004: Coverage Metrics Calculation

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall calculate verification coverage from source items to test items.

Behavior:
- Identify source items (requirements)
- Find linked verification items (tests)
- Calculate coverage percentage: (verified items / total items) × 100
- Report items without verification links

Acceptance Criteria:
- Coverage calculation is accurate to 2 decimal places
- Calculation completes in < 2 seconds for 1000 items
- Unverified items are correctly identified
- Coverage updates when test links are added/removed



</div>

### 5. SRS-005: Policy-Based Compliance Validation and Display

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall validate DHF against configurable compliance policies and display results with evidence.

Behavior:
- Load policy definitions from configuration
- Execute validation rules against DHF items
- Calculate compliance score per policy group
- Collect evidence for each validation result
- Display validation results per policy group
- Show pass/fail status with visual indicators
- Provide detailed evidence for failures
- Support expandable/collapsible result sections

Acceptance Criteria:
- All configured policies are executed
- Validation completes in < 5 seconds for 1000 items
- Compliance score is percentage of passed rules
- Evidence includes specific items and rule results
- All policy results are displayed
- Pass/fail status is clearly indicated
- Results render in < 1 second



</div>

### 6. SRS-006: Change Request Management

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall manage change requests with lifecycle workflow and item tracking.

Behavior:
- Create change requests with auto-generated IDs
- Track affected items in change request
- Enforce change request workflow states
- Prevent editing stable items without approved CR

Acceptance Criteria:
- CR IDs are unique and sequential
- Affected items are correctly tracked
- Stable items cannot be edited without approved CR
- CR workflow transitions follow configured rules



</div>

### 7. SRS-007: Change Impact Tracking

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall automatically track impacted objects and link pull requests to change requests.

Behavior:
- Parse PR descriptions for CR references
- Validate referenced CR exists and is editable
- Identify affected items from PR file changes
- Track all impacted objects in change request
- Update CR with PR information and affected item list

Acceptance Criteria:
- CR references in PR description are detected (format: CR-XXX)
- Invalid CR references are rejected with error
- All affected items are identified from file paths
- Impacted objects are tracked in CR metadata
- CR is updated with PR number, URL, and affected items



</div>

### 8. SRS-008: Configurable Workflow Engine

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall enforce configurable lifecycle workflows for items.

Behavior:
- Load workflow definitions from configuration
- Validate state transitions against workflow rules
- Execute transition criteria before allowing transitions
- Support per-document-type workflow configurations

Acceptance Criteria:
- Invalid transitions are blocked with error message
- Transition criteria are executed in order
- Failed criteria prevent transition
- Workflow configuration errors are detected at startup



</div>

### 9. SRS-009: Template-Based Document Generation

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall generate specification documents from templates.

Behavior:
- Load document templates from configured directory
- Gather item data for template context
- Render templates with item data
- Track document versions automatically

Acceptance Criteria:
- Templates are loaded successfully
- Generated documents include all configured items
- Document version increments on regeneration
- Generation completes in < 10 seconds for 100 items



</div>

### 10. SRS-010: Test Result Integration

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall retrieve and persist test results from the CI/CD pipeline
into the DHF, linking each result to the requirement items it verifies.

Mechanism:
- Test functions embed metadata in their docstrings using @-tags:
    @test_id: TC-SYS-001-001      (optional; inferred from function name if absent)
    @links: SYS-001, SYS-002      (requirement items this TC verifies)
    @reviewer: Alice               (optional; design-review metadata)
    @review_status: approved       (optional)
    @review_date: 2026-01-15       (optional)
- A pytest autouse fixture (tests/conftest.py) reads these tags and injects
  them as compliantflow.* <property> elements into the JUnit XML output.
- The CLI command `compliantflow test import <file> --format junit` parses
  the JUnit XML, extracts TC IDs, statuses, and compliantflow.* properties,
  and persists one record per TC in DHF/test-results/results.yaml.
- After import, verification_status is recomputed for each linked requirement
  item: verified (all TCs PASS), failed (any TC FAIL), not_verified (no results).

TC ID extraction (priority order):
1. compliantflow.id property in JUnit XML
2. Regex on test name: test_TC_SYS_001_001_* -> TC-SYS-001-001

Acceptance Criteria:
- All compliantflow.* properties are extracted and stored correctly
- PASS / FAIL / SKIP statuses are correctly parsed
- Tests with no recognisable TC ID are silently skipped
- Linked requirement items have their verification_status updated after import



</div>

### 11. SRS-011: Configurable Document Type Definitions

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall load and validate document type definitions from configuration.

Behavior:
- Load document types from project_config.yaml
- Validate document type schema (code, name, prefix, directory)
- Support dynamic field definitions per document type
- Load per-type workflow configurations
- Validate allowed parent relationships

Acceptance Criteria:
- Invalid configuration fails at startup with clear error
- All document types have required fields (code, name, prefix)
- Field definitions are accessible via config API
- Workflow configurations are loaded per document type
- Parent relationship rules are enforced



</div>

### 12. SRS-012: CLI Command Implementation

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall implement the `compliantflow` CLI package under `src/compliantflow/`
using the `click` library (already a transitive dependency via streamlit).

Entry point: `python -m compliantflow [--dhf PATH]`
Default DHF path: directory named `DHF` adjacent to the `src/` folder.

Commands and behavior:
- `validate schema / traceability / compliance <GROUP>`: calls `core.validate_schema()`,
  `core.validate_traceability()`, `core.check_compliance()`; exits 1 on errors
- `item list [--type CODE] [--status STATUS] [--search TEXT]`: calls
  `core.get_items_filtered()`; outputs newline-delimited JSON records
- `item get <ID>`: calls `core.get_item(uid)`; outputs JSON; exits 1 if not found
- `item create --type CODE --data JSON [--author NAME] [--cr CR_ID]`: calls
  `core.create_item()`; outputs created item JSON
- `item update <ID> --data JSON [--author NAME]`: calls `core.update_item()`
- `item delete <ID> [--author NAME]`: calls `core.delete_item()`
- `item transitions <ID>`: calls `core.get_available_transitions()`; outputs JSON list
- `item transition <ID> <TO_STATE> [--by NAME]`: calls `core.execute_transition()`
- `cr check-status <CR_ID>`: exits 0 if CR is non-stable, 1 if stable or not found
- `cr update <CR_ID> [--item ID]... [--pr-number N] [--pr-url URL] [--pr-title TITLE]`
- `traceability matrix <TYPE> [TYPE...]`: calls `core.build_traceability_matrix()`
- `traceability chain <ID>`: calls `core.get_item_chain()`; outputs full graph JSON
- `test import <FILE> --format junit [--tester NAME] [--run-id ID] [--commit SHA]`
- `test status <TC_ID>`: outputs stored TC record as JSON
- `test list [--status STATUS]`: lists all stored TC records
- `doc list`: outputs configured doc type codes as JSON
- `doc generate <CODE|ALL>`: calls `core.generate_spec()`; writes markdown file
- `doc export <CODE|ALL>`: regenerates markdown then exports PDF

All commands write human-readable messages to stderr and machine-readable data to stdout.



</div>

### 13. SRS-013: Verification Status Display in Traceability View

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

Software shall compute and display the verification status of each requirement
item in the traceability matrix and item detail views.

Behavior:
- For each requirement item, aggregate all linked TC records from results.yaml
- Compute verification_status: verified (all linked TCs PASS), failed (any TC FAIL),
  not_verified (no linked TC records exist)
- Persist computed verification_status back onto the requirement item
- Display verification_status alongside each item in traceability matrix columns
- Display individual TC pass/fail records in the item detail view

Acceptance Criteria:
- verification_status is recomputed after every test import
- Items with no linked TCs show not_verified
- Items with all PASS TCs show verified
- Items with any FAIL TC show failed
- Status is visible in the traceability matrix without opening the item detail



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 13 |
| **Approved** | 0 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 0.0% (0/13)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2026-03-03  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
