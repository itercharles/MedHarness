# Use Case Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | UC-SPEC |
| **Version** | 1.4 |
| **Generated** | 2026-03-03 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the Use Case for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all Use Cases, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all Use Cases defined in the CompliantFlow system as of 2026-03-03.

---

## 2. Requirements

### 1. UC-001: Manage design history files (DHF)

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A Regulatory Engineer or QA Engineer manages DHF items through their full lifecycle
using CompliantFlow to ensure IEC 62304 and ISO 13485 compliance.

Actor: Regulatory Engineer / QA Engineer

Preconditions:
- The DHF repository is initialised and project_config.yaml is configured

Primary Flow:
1. Engineer opens the relevant document type page (e.g. CRS, SYS, SRS)
2. Engineer creates a new item: enters title, content, and traceability links to parent items
3. System assigns a unique ID, sets status to `draft`, and commits the YAML file to Git
4. Engineer reviews content and ensures all required fields and links are complete
5. Engineer submits the item for review (transitions to `in_review`)
6. Reviewer validates the item against acceptance criteria (field completeness, link validity)
7. Reviewer approves the item (transitions to `approved`)
8. Approved item becomes part of the auditable DHF record; Git history provides the audit trail

Alternative Flows:
- A. Reviewer requests changes: item transitions back to `draft`; engineer reworks and resubmits
- B. Item becomes obsolete: engineer transitions it to `retired` with a documented reason
- C. Bulk operations via CLI: engineer uses `compliantflow item list/get/update` for automation

Postconditions:
- Item is in a defined lifecycle state with a complete audit trail in Git
- Traceability links to parent and child items are maintained
- Compliance with IEC 62304 §5.1.4 (item identification) and §5.1.9 (configuration management) is satisfied



</div>

### 2. UC-002: Verify Traceability

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A Regulatory Engineer assesses traceability coverage across the full requirement
hierarchy and identifies gaps before a design review or regulatory submission.

Actor: Regulatory Engineer / QA Engineer

Preconditions:
- DHF contains items of at least two linked document types (e.g. CRS and SYS)
- Items have traceability links defined (satisfies / derives_from / implements)

Primary Flow:
1. Engineer opens the Traceability view in CompliantFlow
2. Engineer selects a traceability path (e.g. UC → CRS → SYS → SRS → SWDD)
3. System builds a traceability matrix showing all items across the selected path
4. Engineer reviews the matrix: covered links are shown, gaps are highlighted
5. Engineer identifies orphaned items (items with no upstream or downstream link)
6. Engineer drills into a specific item chain to inspect the full upstream/downstream graph
7. Engineer documents any gaps as defects or new requirements for remediation

Alternative Flows:
- A. CLI audit in CI: engineer runs `compliantflow traceability matrix CRS SYS SRS` to
  output a machine-readable matrix and fail the pipeline if coverage drops below threshold
- B. Chain inspection: engineer runs `compliantflow traceability chain SYS-001` to see
  the complete linked graph for a single item

Postconditions:
- All traceability gaps are identified and logged
- IEC 62304 §5.1.1 (software development plan traceability) requirements can be verified



</div>

### 3. UC-003: Generate Specification Documents

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A Regulatory Engineer generates up-to-date specification documents from DHF items
for design reviews, audits, or regulatory submissions.

Actor: Regulatory Engineer / QA Engineer

Preconditions:
- DHF items of the relevant type are in place and approved

Primary Flow:
1. Engineer generate and export the target document type (e.g. SYS, SRS, SYSARCH, RISK)
2. Engineer reviews the generated document for completeness and accuracy, then archives it in the DHF repository.

Alternative Flows:
- A. Regenerate all documents at once: engineer runs `compliantflow doc generate ALL`
  to refresh every configured document type in a single command
- B. Scheduled CI generation: CI pipeline regenerates documents on each merge to main,
  committing the updated markdown so the repository always reflects the latest DHF state

Postconditions:
- Specification document is written to `DHF/documents/specs/`
- Document version is incremented and the generation date is recorded
- PDF is available for offline review and regulatory submission



</div>

### 4. UC-004: Manage Change Requests

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A Regulatory Engineer or Project Manager raises and manages change requests (CRs)
to control modifications to approved DHF items in compliance with ISO 13485 §7.3.7.

Actor: Regulatory Engineer / Project Manager / DevOps Engineer

Preconditions:
- Change control is enabled in project_config.yaml

Primary Flow:
1. Engineer identifies a need for change for DHF, software code or tests.
2. Engineer creates a new CR item: records title, description, justification, and priority
3. System assigns a CR ID (e.g. CR-013) and sets status to `draft`
5. Engineer submits the CR for review (transitions to `in_review`)
6. Reviewer assesses impact on safety, schedule, and linked items; records `impact_assessment`
7. Reviewer approves the CR (transitions to `approved`)
8. Engineer starts implementation (transitions to `implementing`); makes changes to affected items
9. CI pipeline automatically records implementation PRs against the CR via
   `compliantflow cr update CR-013 --item SYS-001 --pr-number 42`
10. On completion, engineer transitions CR to `completed`; linked items are re-approved as needed

Alternative Flows:
- A. CR rejected: reviewer transitions CR to `cancelled` with documented reason
- B. Impact too large: CR is split into multiple smaller CRs before approval
- C. Emergency change: CR approved with expedited review; post-hoc documentation completed

Postconditions:
- All changes to DHF items are traceable to an approved CR
- Implementation PRs are recorded in the CR for audit trail
- Affected items are re-reviewed and re-approved after change



</div>

### 5. UC-005: Check Compliance Policies

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A Regulatory Engineer evaluates the DHF against a defined compliance policy group
(e.g. IEC 62304) to identify non-conformances before a regulatory submission or audit.

Actor: Regulatory Engineer / QA Engineer

Preconditions:
- A compliance policy file (e.g. IEC_62304.yaml) is present in DHF/config/
- DHF items are populated and in a reviewable state

Primary Flow:
1. Engineer opens the Compliance view or runs `compliantflow validate compliance IEC_62304`
2. System loads the policy group and evaluates each policy rule against the current DHF state
3. For each policy, system checks the applicable items (e.g. all SYS items must be approved)
4. System reports each policy as PASS, FAIL, or WARNING with the relevant item IDs and
   the full policy text for traceability
5. Engineer reviews failures and warnings; creates CRs or defects to address each finding
6. Engineer re-runs compliance check after remediation to confirm all policies pass

Alternative Flows:
- A. CI gate: CI pipeline runs compliance check on every PR; fails the build if any
  required policy is violated, preventing non-compliant code from merging
- B. Partial check: engineer validates a single policy group (e.g. only software
  requirements policies) by selecting a specific group ID

Postconditions:
- Compliance status for each policy is recorded and reviewable
- All failures are linked to remediation actions (CRs or defects)
- IEC 62304 §4 (general requirements) and §5 (software development process) coverage is confirmed



</div>

### 6. UC-006: CLI Automation by DevOps Engineer

<div class="requirement-section" markdown="1">

**Status**: <span class="status-"></span>  

#### Description

A DevOps engineer integrates CompliantFlow into a CI/CD pipeline using the CLI.

Primary Flow:
1. CI pipeline checks out code with DHF items
2. Engineer runs `python -m compliantflow validate` to validate all items against schema
3. On pull request, CI runs `python -m compliantflow cr check-status CR-XXX` to verify the CR is open
4. CI detects changed files and runs `python -m compliantflow cr update CR-XXX --item SYS-001 --pr-number 42` to auto-populate the CR
5. Engineer runs `python -m compliantflow item list --type SYS` to audit requirements from a script

The engineer does not start a web server; all operations are command-line only.



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 6 |
| **Approved** | 0 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 0.0% (0/6)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2026-03-03  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
