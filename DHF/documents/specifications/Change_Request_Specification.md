# Change Request Specification

**Document Version:** 1.0  
**Generated:** 2026-03-03  
**Project:** CompliantFlow Project

---

## Document Control

| Field | Value |
|-------|-------|
| Document ID | CR-SPEC |
| Version | 1.0 |
| Status | DRAFT |
| Last Updated | 2026-03-03 |
| Total Change Requests | 20 |

---

## Purpose

This document provides a comprehensive specification of all Change Requests (CRs) in the system. Each CR tracks proposed changes to the product, including their justification, impact assessment, implementation status, and affected items.

---

## Change Request Summary

### By Status

- **DRAFT**: 4 change request(s)
- **IN_REVIEW**: 4 change request(s)
- **APPROVED**: 2 change request(s)
- **IMPLEMENTING**: 1 change request(s)

### By Priority

- **High**: 9 change request(s)
- **Medium**: 3 change request(s)
- **Low**: 1 change request(s)

---

## Change Requests


### CR-001: Add bulk approval feature for requirements

**Status:** APPROVED  
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

#### Implementation Pull Requests

[{'pr_number': 14, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/14', 'title': 'Feature/api based testing'}]


#### Traceability




---


### CR-002: Implement automated traceability report generation

**Status:** DRAFT  
**Priority:** Low  
**Requested By:** Compliance Team  
**Assigned To:** 

#### Description

Add functionality to automatically generate traceability reports on a scheduled basis.
Reports should be generated nightly and stored in a reports directory. This will
support continuous compliance monitoring and reduce manual report generation effort.


#### Justification

- Enables continuous compliance monitoring
- Reduces manual effort for report generation
- Provides historical record of traceability status
- Supports audit preparation


#### Impact Assessment

**New Components:**
- Scheduled task runner (cron or similar)
- Report generation service
- Report storage and archival system

**Configuration:**
- Add scheduling configuration
- Define report formats and templates
- Configure retention policies

**Testing:**
- Test report generation accuracy
- Verify scheduling mechanism
- Test report storage and retrieval

**Risk Assessment:** Medium
- New background service component
- Requires infrastructure for scheduling
- May impact system resources during generation





#### Traceability




---


### CR-003: Automated PR-CR Linking and Traceability System

**Status:** APPROVED  
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

#### Implementation Pull Requests

[{'pr_number': 2, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/2', 'title': '[CR-003] Feature/pr cr automation docs'}, {'pr_number': 3, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/3', 'title': 'refactor: remove YAML file existence check for test IDs, allowing aut…'}, {'pr_number': 4, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/4', 'title': 'Feature/improve cr display UI'}, {'pr_number': 7, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/7', 'title': 'Refactor/dhf requirements restructure'}]


#### Traceability




---


### CR-004: Improve the format customization of frontend style

**Status:** DRAFT  
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

#### Implementation Pull Requests

[{'pr_number': 6, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/6', 'title': 'Feature/property format system'}]


#### Traceability




---


### CR-005: Improve the effectiveness of the auto testing

**Status:** DRAFT  
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

#### Implementation Pull Requests

[{'pr_number': 5, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/5', 'title': 'Feature/user workflow tests'}]


#### Traceability




---


### CR-006: The objects' ID shall be generated automatically and not editable

**Status:** IN_REVIEW  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

The objects' ID shall be generated automatically and not editable

#### Justification

The ID shall not be edit as it cause problems for the reference

#### Impact Assessment

Impact assessment pending.

#### Affected Items

- SRS-001
- TC-SRS-002
- TC-SYS-008
- TC-SYS-010

#### Implementation Pull Requests

[{'pr_number': 8, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/8', 'title': 'feat: Implement automatic ID generation for items, updating core logi…'}]


#### Traceability




---


### CR-007: Defect: the specification generation in system architecture page doesn't work

**Status:** IN_REVIEW  
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

#### Implementation Pull Requests

[{'pr_number': 9, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/9', 'title': 'fix: update system architecture document type code and add CR-007.'}]


#### Traceability




---


### CR-008: Display the linked items for each objects list table

**Status:** IN_REVIEW  
**Priority:** High  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

I want to display the link items and the relationship with other objects, for now the table display "link" without real content. It has been decided to remove the link column

#### Justification

usability

#### Impact Assessment

Impact assessment pending.




#### Traceability




---


### CR-009: Refactor Legacy Links System to Use Relationship Fields

**Status:** IMPLEMENTED  
**Priority:** Medium  
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


### CR-010: Centralize Relationship Configuration

**Status:** IMPLEMENTED  
**Priority:** Medium  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

No description provided.

#### Justification

No justification provided.

#### Impact Assessment

Impact assessment pending.


#### Implementation Pull Requests

[{'pr_number': 11, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/11', 'title': 'feat: Introduce centralized relationship configuration with a new `re…'}]


#### Traceability




---


### CR-011: refactor the status management of object

**Status:** DRAFT  
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

#### Implementation Pull Requests

[{'pr_number': 12, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/12', 'title': 'Feature/cr 011 unified lifecycle'}]


#### Traceability




---


### CR-012: Add CLI layer for CI/CD integration

**Status:** IMPLEMENTING  
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

#### Implementation Pull Requests

[{'pr_number': 19, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/19', 'title': 'feat: Add CLI layer for CI/CD integration (CR-012)'}, {'pr_number': 21, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/21', 'title': 'CR-012: Improve CI policy, remove stale browser deps, deduplicate CRS tests'}, {'pr_number': 22, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/22', 'title': 'CR-012: refactor: Move CompliantFlowCore to compliantflow/ package'}, {'pr_number': 23, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/23', 'title': 'CR-012: refactor: Move CLI to src/cli/, rename pages/ to debug_view/'}, {'pr_number': 24, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/24', 'title': 'CR-012: feat: Add build_traceability_matrix and get_item_chain to domain API'}, {'pr_number': 25, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/25', 'title': 'CR-012: feat: Add traceability matrix and chain CLI commands'}, {'pr_number': 26, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/26', 'title': 'CR-012: Remove get_item_neighbors in favour of get_item_chain'}, {'pr_number': 28, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/28', 'title': 'CR-012: External test result integration via CLI (SYS-033)'}, {'pr_number': 29, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/29', 'title': 'CR-012: Wire test import into CI pipeline (Phase 3.5)'}, {'pr_number': 30, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/30', 'title': 'CR-012: fix: Detect new results.yaml when committing CI test imports'}, {'pr_number': 31, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/31', 'title': 'CR-012: Simplify test result integration - remove register command and audit log'}, {'pr_number': 32, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/32', 'title': 'CR-012: Refresh SRS-010 - remove scanner/provider, align tests with new import mechanism'}, {'pr_number': 36, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/36', 'title': 'CR-012: Fix PDF export - render markdown inside HTML div blocks'}, {'pr_number': 37, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/37', 'title': 'CR-012: Add UC workflows and fix file_path leaking into YAML'}, {'pr_number': 38, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/38', 'title': 'CR-012: Fix CRS completeness - align with UCs, add missing items'}, {'pr_number': 39, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/39', 'title': 'CR-012: Align SYS/SRS with CRS - fix links, content and gaps'}, {'pr_number': 40, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/40', 'title': 'CR-012: Align SYSARCH and SWDD with SYS/SRS hierarchy'}, {'pr_number': 43, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/43', 'title': 'CR-012: Fix CI - phase 3.5 import-results only on pull_request'}, {'pr_number': 44, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/44', 'title': 'CR-012: Remove manual_verifications from project config and YAML items'}, {'pr_number': 45, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/45', 'title': 'CR-012: Remove dead manual_verifications code'}]


#### Traceability




---


### CR-SRS006-TEST: Transition Test CR

**Status:** IN_REVIEW  
**Priority:** Not Set  
**Requested By:** Not Specified  
**Assigned To:** Unassigned

#### Description

Testing transitions

#### Justification

Test

#### Impact Assessment

Impact assessment pending.




#### Traceability




---


### CRS-001: DHF Item Definition and Management

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



**All Related Items:**
- UC-001

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



**All Related Items:**
- UC-002

---


### CRS-003: Change Control by change request

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



**All Related Items:**
- UC-004

---


### CRS-004: Automated Documentation

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



**All Related Items:**
- UC-003

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



**All Related Items:**
- UC-002
- UC-006

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



**All Related Items:**
- UC-005

---


### CRS-013: Item Lifecycle Workflow Management

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



**All Related Items:**
- UC-001

---


## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | | | |
| Reviewer | | | |
| Approver | | | |

---

*End of Change Request Specification*