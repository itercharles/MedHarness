# Software Design Specification Specification

<div class="doc-info">

**Document ID**: SDS-SPEC  
**Version**: 2.6  
**Generated**: 2025-12-21  
**Status**: Draft  
**Project**: CompliantFlow Project

</div>

---

## 1. Introduction

This document specifies the Software Design Specification for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all Software Design Specifications, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all Software Design Specifications defined in the CompliantFlow system as of 2025-12-21.

---

## 2. Requirements

### 1. SDS-001: Graph Data Structure

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Use NetworkX DiGraph to store items as nodes and traceability links as edges.

#### Linked Items

- SYS-002


</div>

### 2. SDS-002: Streamlit Visualization

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Use streamlit-agraph to render interactive traceability graph. Implement dynamic Data Views for item properties and a Compliance Tab for regulatory checks.

#### Linked Items

- SYS-003


</div>

### 3. SDS-003: Policy Engine

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement PolicyEngine to parse Governance documents (Regulations/Procedures) and execute automated checks, generating Compliance Reports.

#### Linked Items

- SYS-006


</div>

### 4. SDS-004: Change Management Module

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  
**Reviewer**: Software Developer  **Review Date**: 2025-12-13  
#### Description

Implementation of the change management system using:

**Data Models:**
- ChangeRequest: Pydantic model with fields for title, description, type, priority, 
  status, affected items, risk assessment, and workflow tracking
- ChangeImpact: Model for impact analysis results with categorized affected items
- Enums: ChangeType, ChangePriority, ChangeStatus

**Core Components:**
- ChangeTracker: CRUD operations with auto-ID generation (CR-001, CR-002, etc.)
- ChangeWorkflow: State machine for workflow transitions with validation
- ImpactAnalyzer: Graph-based impact analysis with MDCG 2020-3 significance assessment

**Storage:**
- YAML files in DHF/change_requests/
- Git integration for version control

**UI:**
- Streamlit page with 3 tabs: Submit, Review, History
- Form validation and real-time status updates
- CSV export functionality

#### Linked Items

- SYS-008


</div>

### 5. SDS-013: Automatic Document Generation with Version Management

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

The system shall provide automatic document generation functionality that:
1. Generates specification documents from YAML item data using Jinja2 templates
2. Automatically increments document version on each regeneration (minor version)
3. Resets document status to "Draft" on each regeneration
4. Saves generated documents as static markdown files for version control
5. Supports PDF export from static markdown files
6. Maintains separate preview state for each document type

Implementation details:
- DocumentGenerator.generate_markdown_spec() reads existing version, increments minor version
- Version format: Major.Minor (e.g., 1.0, 1.1, 1.2)
- Status always reset to "Draft" to ensure proper review workflow
- Templates: requirements_specification.md.j2, test_specification.md.j2
- Configured document types: CRS, SYS, SDS, TC-CRS, TC-SYS, TC-SDS

#### Linked Items

- SYS-008


</div>

### 6. SDS-COMP-001: Compliance Dashboard Page Component

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement Streamlit page (03_Compliance.py) with policy group selector, compliance check button, and results display sections.

#### Linked Items

- SYS-025
- SYS-027


</div>

### 7. SDS-COMP-002: Compliance Score Visualization

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement score calculation, color-coded display (green/yellow/red indicators), and progress bar visualization for compliance percentage.

#### Linked Items

- SYS-026


</div>

### 8. SDS-COMP-003: Policy Results Table and Evidence Display

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement results dataframe with pass/fail icons, policy descriptions merged from definitions, and expandable evidence panels grouped by pass/fail status.

#### Linked Items

- SYS-027


</div>

### 9. SDS-DEF-001: Defect Pydantic Model

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Use Pydantic v2 to define Defect model with fields for id, title, description, severity enum (critical/major/minor/cosmetic), status enum, reported_by, assigned_to, affected_items list, steps_to_reproduce, and timestamps.

#### Linked Items

- SYS-009


</div>

### 10. SDS-DEF-002: Defect Workflow State Machine

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement DefectWorkflow class with state transition validation. Define valid transitions map and methods for assign_defect(), start_investigation(), resolve_defect(), verify_resolution(), close_defect().

#### Linked Items

- SYS-010


</div>

### 11. SDS-DEF-003: Defect Git Integration

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement Git version control integration using GitRepository.commit_file() for all defect create, update, and delete operations with descriptive commit messages and author tracking.

#### Linked Items

- SYS-014


</div>

### 12. SDS-DEF-004: Defect Streamlit UI

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement Streamlit page with three tabs - Report Defect (form with all fields), Manage Defects (filters by status/severity/assignee with expandable cards), Defect History (metrics dashboard and CSV export).

#### Linked Items

- SYS-009
- SYS-015


</div>

### 13. SDS-DEF-005: Defect Root Cause Fields

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Add root_cause and resolution fields to Defect model. Implement validation in DefectWorkflow.resolve_defect() to require both fields before allowing status change to resolved.

#### Linked Items

- SYS-011


</div>

### 14. SDS-DEF-006: Defect Verification Fields

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Add verification field to Defect model. Implement validation in DefectWorkflow to enforce resolved → verified → closed sequence, preventing direct closure without verification.

#### Linked Items

- SYS-012


</div>

### 15. SDS-DEF-007: Defect Traceability Fields

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Add affected_items (list) and related_change_request (optional string) fields to Defect model. Implement multiselect UI component in Streamlit to link defects to existing items.

#### Linked Items

- SYS-013


</div>

### 16. SDS-DOCGEN-001: Document Generator Module

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Create a DocumentGenerator class that generates PDF documents from Jinja2 templates.

**Responsibilities**:
- Load Jinja2 templates from DHF/templates/ directory
- Render templates with data from CompliantFlowCore
- Convert markdown to HTML with CSS styling
- Export HTML to PDF using WeasyPrint
- Support custom Jinja2 filters (status_badge, format_date)

**Key Methods**:
- `generate_requirements_spec(doc_type_code: str) -> Path`
- `generate_traceability_matrix() -> Path`
- `generate_release_documentation(release_id: str) -> Path`
- `_export_pdf(markdown_content: str, filename: str) -> Path`

#### Linked Items

- SYS-021


</div>

### 17. SDS-DOCGEN-002: Jinja2 Template System

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement Jinja2 template rendering system for document generation.

**Template Files** (in DHF/templates/):
- requirements_specification.md.j2 - For CRS/SYS/SDS specs
- traceability_matrix.md.j2 - For traceability matrices
- release_documentation.md.j2 - For release packages

**Custom Filters**:
- status_badge: Format status as emoji badge (✅ Approved, 📝 Draft, etc.)
- format_date: Format ISO dates to readable format (YYYY-MM-DD)

**Template Data Structure**:
- doc_type_code, doc_type_name, project_name
- version, generation_date, status
- items (list of requirement/test items)
- traceability_chains, coverage, orphans (for matrix)

#### Linked Items

- SYS-021


</div>

### 18. SDS-DOCGEN-003: PDF Export Pipeline

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement PDF export using WeasyPrint library.

**Pipeline Steps**:
1. Render Jinja2 template → Markdown
2. Convert Markdown to HTML using markdown library
3. Wrap HTML in template with CSS styling
4. Generate PDF using WeasyPrint

**CSS Styling** (DHF/templates/styles/default.css):
- Professional typography (Arial, line-height 1.6)
- Styled headings with colors and borders
- Table formatting with borders and header styling
- Page margins (2cm)

**Output**:
- PDF files saved to /tmp/ directory
- Return Path object for download

#### Linked Items

- SYS-021


</div>

### 19. SDS-DOCGEN-004: Traceability Matrix Builder

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Build traceability matrix showing CRS → SYS → SDS → Test chains.

**Data Structure**:
Each chain contains:
- crs_id, crs_title
- sys_id, sys_title (if linked)
- sds_id, sds_title (if linked)
- test_id (if linked)
- status (overall chain status)

**Coverage Metrics**:
- crs_to_sys: % of CRS with SYS links
- sys_to_sds: % of SYS with SDS links
- req_to_test: % of requirements with tests

**Orphan Detection**:
- CRS without SYS
- SYS without SDS
- Requirements without tests

#### Linked Items

- SYS-021


</div>

### 20. SDS-DOCGEN-005: UI Export Button Integration

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Add PDF export button to Streamlit UI pages.

**Location**: In render_table_section() of universal_page_template.py

**UI Layout**:
- 3-column layout: [Items Header | Export PDF | New]
- Export PDF button triggers document generation
- Show download link after generation
- Display progress indicator during generation

**User Flow**:
1. User clicks "📄 Export PDF" button
2. System generates PDF for current document type
3. Download link appears
4. User clicks to download PDF

#### Linked Items

- SYS-021


</div>

### 21. SDS-DYNPAGE-001: Page Generator Module

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement page_generator.py module with create_doc_page_function() to create unique page functions and generate_doc_type_pages() to build sorted page list from configuration.

#### Linked Items

- SYS-028
- SYS-029


</div>

### 22. SDS-DYNPAGE-002: Main Application Navigation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Update app.py to use st.navigation() with dynamically generated pages list, including Home page, document type pages, and special pages (Traceability, Compliance).

#### Linked Items

- SYS-028


</div>

### 23. SDS-REL-001: Release Pydantic Model

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Use Pydantic v2 to define Release model with fields for version, status enum (planning, developing, testing, released), release_date, included_change_requests, test_summary, defect_summary, release_notes, manual_verifications (dict tracking verifier and timestamp), and stage_approvals (dict tracking approver and timestamp for each transition).

#### Linked Items

- SYS-016


</div>

### 24. SDS-REL-002: Release Verification Logic

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement ReleaseValidator class with methods to check requirement coverage, verify all tests pass, and check for open critical defects. Implement WorkflowCriteriaChecker class to evaluate configurable criteria from workflow_criteria.yaml including automated checks (field validation, counts, percentages) and manual verification tracking.

#### Linked Items

- SYS-017


</div>

### 25. SDS-REL-003: Release Workflow State Machine

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement release state transitions with validation - planning → developing → testing → released. Each transition requires approver identity and must pass all criteria defined in DHF/config/workflow_criteria.yaml. Track all stage approvals with timestamp and approver name.

#### Linked Items

- SYS-018


</div>

### 26. SDS-REL-004: Release Report Generator

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement report generation using Markdown templates to create traceability matrix, test summary, defect report, and release notes.

#### Linked Items

- SYS-019


</div>

### 27. SDS-REL-005: Release Streamlit UI

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement Streamlit page with three tabs - Create Release (form), Manage Releases (status and actions), Release Reports (view and export documentation). Implement reusable UI components in ui_components.py for manual verification expanders, stage approval forms, and criteria checklists.

#### Linked Items

- SYS-016
- SYS-019


</div>

### 28. SDS-REL-006: Workflow Criteria Configuration

<div class="requirement-section">

**Status**: <span class="status-draft">DRAFT</span>  

#### Description

Implement configurable workflow criteria system using YAML configuration file (DHF/config/workflow_criteria.yaml) to define transition requirements. Support multiple check types - field validation, count checks, percentage thresholds, manual verifications, and validation status checks. Allow criteria to be marked as required or warning-only.

#### Linked Items

- SYS-017
- SYS-018


</div>

### 29. SDS-SOUP-001: SOUP Document Type Configuration

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implements SOUP document type in project configuration with the following properties:

**Properties**:
- id, title, content: Standard identification fields
- name, version, manufacturer: Package identification
- license, homepage: Legal and reference information
- cve_count, risk_rating: Security assessment from external tools
- safety_class: IEC 62304 safety classification (A/B/C)
- purpose: Documented rationale for SOUP usage (IEC 62304 5.3.4)
- verification_method: How SOUP is verified
- links: Traceability to SYS requirements

**Lifecycle States**:
- draft: Initial state after import
- under_review: Submitted for approval
- approved: Verified and approved for use
- rejected: Not approved for use

**Transition Criteria**:
- Draft → Under Review: Requires purpose, safety class, and SYS requirement link
- Under Review → Approved: Requires verification completion
- Under Review → Rejected: Requires rejection reason

#### Linked Items

- SYS-022


</div>

### 30. SDS-SOUP-002: SOUP Import Interface

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implements import interface for SOUP data from external scanning tools.

**Supported Formats**:
- JSON: Veracode, Snyk output format
- CSV: OWASP Dependency-Check format
- TXT: requirements.txt format
- YAML: CompliantFlow native format

**Import Process**:
1. Parse input file based on format
2. Normalize data to CompliantFlow SOUP schema
3. Create SOUP items in draft status
4. Auto-populate metadata from external tool
5. Set default safety class to C (most conservative)

**SOUPImporter Class**:
- import_file(file_path, format): Main import method
- _normalize_soup_item(raw_item): Data normalization
- _import_json(), _import_csv(), _import_txt(), _import_yaml(): Format-specific parsers

**Design Rationale**:
CompliantFlow focuses on workflow management rather than dependency scanning.
This allows integration with best-in-class security tools (Veracode, Snyk)
while maintaining clean separation of concerns.

#### Linked Items

- SYS-022


</div>

### 31. SDS-SOUP-003: SOUP Workflow and Traceability

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implements SOUP approval workflow and traceability to system requirements.

**Workflow Integration**:
- Leverages DynamicWorkflowEngine for state transitions
- Enforces approval criteria before state changes
- Tracks reviewer and review date
- Supports manual verification for approval

**Traceability Model**:
SOUP → SYS Requirements (one-to-many)

Each SOUP item must link to at least one SYS requirement to document:
- Why the SOUP is needed (IEC 62304 5.3.4)
- Which system functions depend on it
- Impact analysis for CVE vulnerabilities
- Change impact when upgrading SOUP versions

**UI Integration**:
- Auto-generated SOUP page using universal_page_template
- Workflow buttons for state transitions
- Criteria validation before approval
- Link management to SYS requirements

**Approval Criteria**:
1. Purpose documented (rationale for use)
2. Safety class assigned (A/B/C)
3. Linked to SYS requirement (traceability)
4. Verification completed (manual check)

#### Linked Items

- SYS-022


</div>

### 32. SDS-TEST-001: Test Automation System Design

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Verification Method**: 1. Run pytest test suite locally
2. Verify all 58 tests pass
3. Push to GitHub and trigger workflow
4. Verify test results appear in UI
5. Check test status badges display correctly
6. Verify caching works (no excessive API calls)
  
#### Description

## Purpose

This document specifies the design of the automated test system that integrates with GitHub Actions to provide continuous testing and real-time test status updates.

## Design Overview

The test automation system consists of three main components:
1. **Test Execution Layer** - pytest-based automated tests
2. **CI/CD Integration** - GitHub Actions workflow
3. **Results Integration** - Test results provider and UI display

## Component Specifications

### 1. Test Results Provider (`src/test_results/provider.py`)

**Purpose:** Abstract interface for fetching test results from different sources

**Interface:**
```python
class TestResultsProvider(ABC):
    @abstractmethod
    def get_test_results(self) -> Dict[str, TestResult]:
        """Fetch test results from provider"""
        pass
    
    def get_test_status(self, test_id: str) -> str:
        """Get status for specific test ID"""
        results = self.get_test_results()
        return results.get(test_id, {}).get('status', 'PENDING')
```

**Implementation:** Supports pluggable providers (GitHub Actions, local files, etc.)

### 2. GitHub Actions Provider (`src/test_results/github_provider.py`)

**Purpose:** Fetch test results from GitHub Actions artifacts

**Key Methods:**
```python
class GitHubActionsProvider(TestResultsProvider):
    def __init__(self, owner, repo, workflow_name, artifact_name, token):
        # Initialize with GitHub repository details
        
    def fetch_latest_test_results(self) -> Dict:
        # 1. Get latest workflow run
        # 2. Find test-results artifact
        # 3. Download and extract artifact
        # 4. Parse JUnit XML
        # 5. Return test results dictionary
        
    def parse_junit_xml(self, xml_content: str) -> Dict:
        # Parse JUnit XML format
        # Extract test cases and results
        # Map to internal format
```

**Token Handling:**
- Loads GITHUB_TOKEN from .env file
- Reloads environment to bypass Streamlit caching
- Uses token for authenticated GitHub API requests

**Caching:**
- Results cached in Streamlit session state
- Cache key: `test_results_cache`
- Prevents excessive API calls

### 3. Test Scanner (`src/test_results/scanner.py`)

**Purpose:** Scan test files to extract test IDs and metadata

**Key Methods:**
```python
class TestScanner:
    def scan_test_files(self, test_dir: Path) -> List[TestInfo]:
        # Find all test_*.py files
        # Extract test functions
        # Parse docstrings for @test_id
        # Return list of test information
        
    def extract_test_id(self, func) -> Optional[str]:
        # Parse docstring
        # Look for @test_id: TC-XXX-XXX pattern
        # Return test ID if found
```

**Test ID Format:**
```python
def test_TC_SYS_004_governance_parsing():
    \"\"\"
    Verify Governance Parsing
    
    @links: SYS-005
    @test_id: TC-SYS-004
    \"\"\"
```

### 4. Configuration Integration

**project_config.yaml:**
```yaml
test_integration:
  provider: github  # or 'local'
  github:
    owner: itercharles
    repo: CompliantFlow
    workflow_name: test.yml
    artifact_name: test-results
```

**ProjectConfig Model:**
```python
class TestIntegrationConfig(BaseModel):
    provider: str
    github: Optional[GitHubConfig] = None
    local: Optional[LocalConfig] = None

class ProjectConfig(BaseModel):
    # ... other fields
    test_integration: Optional[TestIntegrationConfig] = None
```

## Data Flow

```
1. Developer commits code
2. GitHub Actions triggers test.yml workflow
3. pytest runs all tests
4. JUnit XML results generated
5. test-results artifact uploaded
6. UI requests test results
7. GitHubActionsProvider fetches artifact
8. XML parsed and mapped to test IDs
9. Results displayed in UI with badges
```

## UI Integration

### Universal Page Template

**Test Status Display:**
```python
# Get test results
provider = get_test_results_provider(core.config)
test_status = provider.get_test_status(item['id'])

# Display badge
if test_status == 'PASS':
    st.success('✅ PASS')
elif test_status == 'FAIL':
    st.error('❌ FAIL')
else:
    st.warning('⏳ PENDING')
```

### Test Case Pages

Generated dynamically from configuration:
- TC-SYS (System Tests) - Page 9
- TC-CRS (Validation Tests) - Page 10
- TC-SDS (Design Tests) - Page 11

## Error Handling

**GitHub API Errors:**
- Network failures: Return cached results or empty dict
- Authentication errors: Log warning, return PENDING status
- Rate limiting: Implement exponential backoff

**XML Parsing Errors:**
- Malformed XML: Log error, skip invalid test cases
- Missing test IDs: Use test function name as fallback

## Performance Considerations

**API Rate Limits:**
- Unauthenticated: 60 requests/hour
- Authenticated: 5000 requests/hour
- Solution: Cache results in session state

**Artifact Size:**
- JUnit XML typically < 100KB
- Download time: < 1 second
- Parsing time: < 100ms

## Security

**Token Storage:**
- GITHUB_TOKEN stored in .env file
- .env file in .gitignore
- Never commit tokens to repository

**Token Permissions:**
- Read-only access to repository
- No write permissions required
- Minimal scope: `repo:status` or `public_repo`

## Testing Strategy

**Unit Tests:**
- Test XML parsing logic
- Test test ID extraction
- Test configuration loading

**Integration Tests:**
- Test GitHub API integration
- Test end-to-end workflow
- Mock GitHub API for reliability

## Dependencies

**Required Packages:**
- requests - HTTP client for GitHub API
- python-dotenv - Environment variable loading
- xml.etree.ElementTree - XML parsing (stdlib)

**Optional Packages:**
- pytest - Test framework
- pytest-cov - Coverage reporting

## Future Enhancements

1. **Multiple Providers:** Support Jenkins, CircleCI, etc.
2. **Historical Trends:** Track test pass/fail rates over time
3. **Notifications:** Alert on test failures
4. **Parallel Execution:** Speed up test runs
5. **Test Retries:** Automatic retry for flaky tests

#### Linked Items

- SYS-020
- SYS-021
- SYS-022
- ARCH-006


</div>

### 33. SDS-TRACE-001: TraceabilityMatrix Pydantic Model

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement TraceabilityMatrix model with name (str), description (str), and path (List[str]) fields in config.py.

#### Linked Items

- SYS-021


</div>

### 34. SDS-TRACE-002: Recursive Chain Builder Function

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement recursive function to traverse trace paths, creating DataFrame rows for each complete or incomplete chain, with support for multiple child matches.

#### Linked Items

- SYS-022


</div>

### 35. SDS-TRACE-003: Status Warning Helper Function

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement should_show_warning function to check item status against lifecycle's stable states, raising ValueError for missing configuration.

#### Linked Items

- SYS-023


</div>

### 36. SDS-TRACE-004: Matrix Table UI Component

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Implement Streamlit UI with matrix dropdown, statistics display, and dynamic column configuration based on trace path.

#### Linked Items

- SYS-021
- SYS-024


</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 36 |
| **Approved** | 15 |
| **Draft** | 21 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 41.7% (15/36)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2025-12-21  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
