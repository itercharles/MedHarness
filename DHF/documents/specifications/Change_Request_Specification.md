# Change Request Specification

**Document Version:** 1.0  
**Generated:** 2026-01-10  
**Project:** CompliantFlow Project

---

## Document Control

| Field | Value |
|-------|-------|
| Document ID | CR-SPEC |
| Version | 1.0 |
| Status | DRAFT |
| Last Updated | 2026-01-10 |
| Total Change Requests | 18 |

---

## Purpose

This document provides a comprehensive specification of all Change Requests (CRs) in the system. Each CR tracks proposed changes to the product, including their justification, impact assessment, implementation status, and affected items.

---

## Change Request Summary

### By Status

- **DRAFT**: 4 change request(s)
- **IN_REVIEW**: 3 change request(s)
- **APPROVED**: 9 change request(s)

### By Priority

- **High**: 8 change request(s)
- **Medium**: 4 change request(s)
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
- CRS-012
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
- CRS-005
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

- SYS-TRANS-001
- TC-SRS-006
- TC-SRS-008
- TC-SRS-015

#### Implementation Pull Requests

[{'pr_number': 12, 'pr_url': 'https://github.com/itercharles/CompliantFlow/pull/12', 'title': 'Feature/cr 011 unified lifecycle'}]


#### Traceability




---


### CRS-001: Requirement definition

**Status:** APPROVED  
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

**Status:** APPROVED  
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

**Status:** APPROVED  
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

**Status:** APPROVED  
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


### CRS-005: Architecture definition

**Status:** APPROVED  
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


### CRS-008: Automated Test Integration

**Status:** APPROVED  
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



**All Related Items:**
- UC-002

---


### CRS-011: Regulatory Compliance Validation

**Status:** APPROVED  
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


## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | | | |
| Reviewer | | | |
| Approver | | | |

---

*End of Change Request Specification*