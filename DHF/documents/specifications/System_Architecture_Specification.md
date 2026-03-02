# System Architecture Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | ARCH-SPEC |
| **Version** | 1.0 |
| **Generated** | 2025-12-21 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the system architecture for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides comprehensive documentation of architectural decisions, design rationale, and technical implementation details.

### 1.1 Purpose

This document provides detailed architecture specifications including:
- System architecture and component design
- Data models and storage architecture
- Technology stack and implementation choices
- Design rationale and alternatives considered
- Interface definitions and integration points

### 1.2 Scope

This specification covers all architecture components defined in the CompliantFlow system as of 2025-12-21.

---

## 2. Architecture Components

### 1. ARCH-001: CompliantFlow System Architecture

<div class="architecture-section">

**Status**: <span class="status-draft">DRAFT</span>  
**Component**: System  **Architecture Type**: system  
#### Overview

## Overview
CompliantFlow follows a layered architecture pattern with clear separation of concerns.

## Layers
1. **Presentation Layer**: Streamlit UI
   - Universal page template
   - Dynamic form generation
   - Workflow transition UI

2. **Business Logic Layer**
   - CompliantFlowCore: Central orchestrator and lifecycle manager
   - GraphEngine: Traceability analysis
   - LifecycleMethods: State transition logic

3. **Data Access Layer**
   - ItemLoader: YAML file reading
   - ItemSaver: YAML file writing with validation
   - GitRepository: Version control integration

4. **Storage Layer**
   - YAML files for item storage
   - Git for version control and audit trail
   - File-based configuration

## Component Diagram
```
┌─────────────────────────────────────────┐
│         Streamlit UI Pages              │
│  (Universal Template + Page Generator)  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       CompliantFlowCore                 │
│  (Orchestration + API)                  │
└──────┬──────────┬──────────┬────────────┘
       │          │          │
  ┌────▼───┐  ┌──▼────┐  ┌──▼─────┐
  │Lifecycle │  │ Graph │  │ Item   │
  │Methods   │  │Engine │  │Manager │
  └──────────┘  └───────┘  └────┬───┘
                               │
                  ┌────────────▼──────────┐
                  │  ItemLoader/Saver     │
                  │  + GitRepository      │
                  └────────────┬──────────┘
                               │
                  ┌────────────▼──────────┐
                  │  YAML Files + Git     │
                  └───────────────────────┘
```

#### Design Rationale

Layered architecture chosen for:
- **Separation of Concerns**: Each layer has a single responsibility
- **Testability**: Layers can be tested independently
- **Maintainability**: Changes isolated to specific layers
- **IEC 62304 Compliance**: Clear software architecture documentation
- **Flexibility**: Easy to swap implementations (e.g., different storage backends)


#### Alternatives Considered

**Microservices Architecture**
- Rejected: Too complex for single-user desktop application
- Overhead of inter-service communication not justified

**Monolithic Architecture**
- Rejected: Poor maintainability and testability
- Difficult to extend with new document types

**Plugin Architecture**
- Considered but deferred: Current config-driven approach provides sufficient flexibility
- May revisit for future extensibility needs


#### Technology Stack

- **Python 3.11+**: Core language
- **Streamlit**: Web UI framework
- **Pydantic v2**: Data validation and serialization
- **PyYAML**: Configuration and data persistence
- **NetworkX**: Graph analysis for traceability
- **GitPython**: Version control integration
- **Jinja2**: Template rendering for document generation


#### Interfaces

**External Interfaces**:
- File system (YAML read/write)
- Git repository (version control)
- Web browser (Streamlit UI)

**Internal Interfaces**:
- CompliantFlowCore API (get_item, create_item, update_item, transition_item)
- LifecycleMethods API (get_state_info, get_available_transitions, validate_transition)
- GraphEngine API (build_graph, find_orphans, calculate_coverage)


#### Related Requirements

- SYS-001
- SYS-002
- SYS-003

</div>

### 2. ARCH-002: Data Model and Storage Architecture

<div class="architecture-section">

**Status**: <span class="status-review">REVIEW</span>  
**Component**: Data  **Architecture Type**: data  
#### Overview

## Data Model

### Item Model
All traceability items follow a common base structure:
```python
class Item(BaseModel):
    uid: str                    # Unique identifier (alias: id)
    text: str                   # Main content (alias: content)
    title: Optional[str]        # Human-readable title
    status: str                 # Current lifecycle state
    links: List[str]            # Links to other items
    verification_status: Optional[VerificationStatus]
    manual_verifications: Optional[Dict]
    # ... additional properties per doc type
```

### Configuration Model
```python
class DocTypeConfig(BaseModel):
    code: str                   # Document type code (e.g., "SYS")
    name: str                   # Display name
    prefix: str                 # ID prefix (e.g., "SYS-")
    directory: Optional[str]    # Storage directory
    properties: List[str]       # Allowed fields
    lifecycle: LifecycleConfig  # Workflow definition
    relations: List[Relation]   # Traceability relations
```

## Storage Architecture

### Directory Structure
```
DHF/
├── config/
│   └── project_config.yaml    # Master configuration
├── items/
│   ├── 01_req_crs/           # Customer Requirements
│   ├── 02_req_sys/           # System Requirements
│   ├── 04_req_sds/           # Design Specifications
│   ├── 05_tc_sys/            # System Tests
│   ├── 06_tc_crs/            # Validation Tests
│   ├── 07_tc_sds/            # Design Tests
│   ├── 08_defect/            # Defects
│   ├── 09_cr/                # Change Requests
│   ├── 10_release/           # Releases
│   ├── 11_soup/              # SOUP Items
│   └── 12_arch/              # Architecture Specs
└── governance/
    └── IEC_62304.yaml        # Compliance policies
```

### File Format
- **Format**: YAML (human-readable, Git-friendly)
- **Naming**: `{ID}.yaml` (e.g., `SYS-001.yaml`)
- **Validation**: Pydantic models ensure data integrity
- **Serialization**: `mode='json'` for proper enum handling

## Version Control Integration

### Git-Based Audit Trail
- Every item change creates a Git commit
- Commit message includes: action, item ID, author
- Complete history available via `git log`
- Tamper-evident audit trail

### Benefits
- **Immutable History**: Cannot alter past changes
- **Branching**: Support for parallel development
- **Rollback**: Easy to revert to previous versions
- **Compliance**: Meets IEC 62304 audit requirements

#### Design Rationale

File-based storage with Git version control chosen for:

**Human-Readable Format**
- YAML is easy to read and edit manually
- No special tools required for inspection
- Facilitates code review and collaboration

**Git-Friendly**
- Text-based format works well with Git
- Meaningful diffs for changes
- Merge conflict resolution possible

**No Database Dependency**
- Simpler deployment (no DB setup)
- Easier backup (just copy directory)
- Better for small to medium datasets

**Regulatory Compliance**
- Git provides required audit trail
- File-based storage is transparent
- Easy to archive for regulatory submission


#### Alternatives Considered

**SQL Database (SQLite/PostgreSQL)**
- Rejected: Adds complexity and deployment overhead
- File-based approach sufficient for expected data volume
- Git history provides better audit trail than DB triggers

**NoSQL Database (MongoDB)**
- Rejected: Overkill for structured, validated data
- YAML + Pydantic provides similar schema flexibility

**JSON Files**
- Considered: Similar to YAML but less human-readable
- YAML chosen for better readability and comments support


#### Technology Stack

- **PyYAML**: YAML parsing and serialization
- **Pydantic v2**: Data validation and type safety
- **GitPython**: Git operations automation
- **Pathlib**: File system operations


#### Interfaces

**ItemLoader Interface**:
- `load_item(uid: str) -> Item`
- `load_all_items() -> List[Item]`
- `load_items_by_prefix(prefix: str) -> List[Item]`

**ItemSaver Interface**:
- `save(item: Item, author: str) -> Path`
- `_get_directory_for_prefix(prefix: str) -> Path`
- `_build_prefix_map() -> Dict[str, str]`

**GitRepository Interface**:
- `commit_item_change(uid: str, file_path: Path, action: str, author: str)`
- `get_file_history(file_path: Path) -> List[Dict]`


#### Related Requirements

- SYS-003
- SYS-004

</div>

### 3. ARCH-003: Configuration-Driven Architecture

<div class="architecture-section">

**Status**: <span class="status-draft">DRAFT</span>  
**Component**: Configuration  **Architecture Type**: software  
#### Overview

## Overview
CompliantFlow uses a configuration-driven architecture where all document types, workflows, and UI behavior are defined in `project_config.yaml` rather than hardcoded in the application.

## Core Principle: Single Source of Truth

The `project_config.yaml` file serves as the single source of truth for:
- Document type definitions
- Workflow lifecycles and transitions
- Validation criteria
- UI configuration (icons, page numbers)
- Traceability relationships
- Field definitions and properties

## Benefits

### 1. Zero Code Changes for New Types
Adding a new document type requires only:
1. Add configuration to `project_config.yaml`
2. Create directory for items
3. Optionally generate page file

No Python code changes needed!

### 2. Integrated Lifecycle Management
Workflows are executed by interpreting configuration:
```yaml
lifecycle:
  states:
    - {id: draft, label: "Draft", is_initial: true}
    - {id: approved, label: "Approved"}
  transitions:
    - from: draft
      to: approved
      criteria:
        - {check_type: "field_not_empty", field: "content"}
```

The `CompliantFlowCore` delegates to `LifecycleMethods` to enforce these rules automatically.

### 3. Universal UI Template
Single page template (`universal_page_template.py`) renders all document types:
- Reads doc type configuration
- Generates forms dynamically
- Shows workflow transitions based on current state
- Displays metrics from lifecycle states

### 4. Validation Criteria Framework
Extensible validation system:
- `field_not_empty`: Check field has value
- `linked_items_approved`: Check linked items status
- `manual`: Require manual verification
- Easy to add new check types

## Architecture Pattern: Interpreter

CompliantFlow implements the **Interpreter Pattern**:
- Configuration is the "language"
- CompliantFlowCore is the "interpreter"
- Runtime behavior determined by configuration

## Configuration Schema

```yaml
doc_types:
  - code: TYPE_CODE
    name: "Display Name"
    prefix: "PREFIX-"
    directory: "folder_name"
    properties: [list of allowed fields]
    
    relations:
      - target: OTHER_TYPE
        type: relationship_type
        label: display_label
    
    icon: "🔧"
    page_enabled: true
    page_number: 5
    
    lifecycle:
      states: [...]
      transitions: [...]
```

#### Design Rationale

Configuration-driven architecture chosen for:

**Flexibility**
- Easy to adapt to different regulatory frameworks
- Customize workflows per organization
- No code changes for common modifications

**Maintainability**
- Single file to understand system behavior
- Changes are declarative, not imperative
- Reduced code complexity

**Compliance**
- Configuration is version-controlled
- Changes to workflows are auditable
- Clear documentation of system behavior

**Extensibility**
- New document types without code changes
- New validation criteria via configuration
- Custom fields per document type


#### Alternatives Considered

**Hardcoded Document Types**
- Rejected: Requires code changes for each new type
- Not flexible enough for different use cases
- Difficult to maintain as types grow

**Database-Driven Configuration**
- Rejected: Adds complexity
- YAML file is simpler and version-controlled
- No need for migration scripts

**Plugin Architecture**
- Considered: More complex than needed
- Configuration approach provides sufficient flexibility
- Could be added later if needed


#### Technology Stack

- **PyYAML**: Configuration parsing
- **Pydantic**: Configuration validation
- **Python dataclasses**: Configuration models


#### Interfaces

**ProjectConfig Interface**:
- `get_doc_type(code: str) -> DocTypeConfig`
- `get_doc_type_by_prefix(prefix: str) -> DocTypeConfig`

**DocTypeConfig Interface**:
- `code: str`
- `name: str`
- `prefix: str`
- `directory: Optional[str]`
- `properties: List[str]`
- `lifecycle: LifecycleConfig`
- `relations: List[Relation]`


#### Related Requirements

- SYS-001
- SYS-005

</div>

### 4. ARCH-004: Fail-Fast Configuration Validation Strategy

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

The system employs fail-fast validation for lifecycle and stable state configuration, throwing explicit errors rather than using fallback defaults.





#### Related Requirements

- SYS-023

</div>

### 5. ARCH-005: Configuration-Driven UI Architecture

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

The system employs a configuration-driven architecture where UI pages are generated dynamically from YAML configuration rather than hardcoded files. This reduces code duplication, improves maintainability, and enables runtime customization without code changes.





#### Related Requirements

- SYS-028

</div>

### 6. ARCH-006: Test Automation and CI/CD Architecture

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  
**Component**: Testing  **Architecture Type**: system  
#### Overview

## Overview

CompliantFlow implements a hybrid test verification system that combines automated pytest tests with manual test case management. The system integrates with GitHub Actions for continuous testing and provides real-time test status updates in the UI.

## Architecture Components

### 1. Test Execution Layer

**Automated Tests**
- Tests organised under `tests/sys/` (SYS API tests), `tests/srs/` (SRS unit tests),
  `tests/crs/` (CRS scenario tests)
- Framework: pytest; any framework that produces JUnit XML is supported
- Test function names follow the convention `test_TC_SYS_001_001_*` to embed TC IDs

**Metadata embedding**
- Each test embeds traceability metadata in its docstring using `@`-tags:
  `@links`, `@reviewer`, `@review_status`, `@review_date`
- A pytest autouse fixture (`tests/conftest.py`) reads the tags and injects
  `compliantflow.*` properties into the JUnit XML output automatically
- Helper functions in `tests/utils/docstring_parser.py` are shared between
  the fixture and the SRS-010 unit tests

### 2. CI/CD Integration (GitHub Actions)

**Workflow Configuration**
```
Phase 1  pytest tests/srs/   --junitxml=srs-results.xml
Phase 2  pytest tests/sys/   --junitxml=sys-results.xml
Phase 3  pytest tests/crs/   --junitxml=crs-results.xml
Phase 3.5  compliantflow test import *.xml --format junit \
             --tester "GitHub Actions" --run-id $RUN_ID \
             --commit $SHA
         git add DHF/test-results/results.yaml && git commit
Phase 4  compliantflow cr update CR-NNN --item ...   (PR only)
```

### 3. Test Results Integration

**Framework-agnostic boundary**

```
tests/  (framework-specific adapter)
  conftest.py               pytest autouse fixture:
  utils/docstring_parser.py   reads @-tags → record_property()
                                             ↓
                              JUnit XML  <compliantflow.*>
────────────────────────────── boundary ──────────────────
src/  (framework-agnostic core)
  test_results/junit_parser.py   parse compliantflow.* properties
  test_results/result_store.py   persist to results.yaml
```

The core (`src/`) only consumes JUnit XML. Any test framework that can
write `compliantflow.*` `<property>` elements — or whose test names follow
the `TC-SYS-NNN` naming convention — is compatible without code changes.

**Data Flow**
```
Test execution → JUnit XML → compliantflow test import → results.yaml
                                                        → verification_status
                                                          updated on linked items
```

**Storage**: `DHF/test-results/results.yaml` — one record per TC ID.
Git history is the audit trail.

### 4. UI Integration

**Test Status Display**
- Traceability matrix shows `testing_status` from ResultStore per TC
- Color-coded badges (PASS / FAIL / SKIP / PENDING)
- Linked requirement items show computed `verification_status`

## Test Automation Strategy

### Automated vs Manual Tests

**Automated (pytest):**
- Unit tests for core functionality
- Integration tests for workflows
- API/backend tests
- Configuration validation
- Fast feedback (< 5 seconds)

**Manual:**
- UI/UX validation
- End-to-end user workflows
- Regulatory compliance verification
- Exploratory testing

### Test ID Mapping

TC IDs are embedded in test function names and/or docstrings:
```python
def test_TC_SYS_001_001_object_creation(test_dhf_root):
    """
    TC-SYS-001-001: Object creation validation

    @test_id: TC-SYS-001-001   # optional; inferred from function name if absent
    @links: SYS-001
    @reviewer: Alice
    @review_status: approved
    @review_date: 2026-01-15
    """
```

The pytest autouse fixture extracts all tags and injects them into
JUnit XML `<properties>`. `compliantflow test import` then reads the
XML and persists the data into `DHF/test-results/results.yaml`.

## Technology Stack

**Testing Framework:**
- pytest - Test execution
- pytest-cov - Coverage reporting

**CI/CD:**
- GitHub Actions - Workflow automation
- JUnit XML - Test result format

**Integration:**
- GitPython - Git operations
- xml.etree.ElementTree - JUnit XML parsing

**Dependencies:**
- pydantic>=2.0 - Data validation
- python-dotenv - Environment variables

## Security Considerations

**GitHub Actions token** (`secrets.GITHUB_TOKEN`):
- Used only to push commits back to the branch (Phase 3.5 and Phase 4)
- Minimum required permission: `contents: write`, `pull-requests: write`
- No GitHub API calls are made for test result fetching

## Performance Characteristics

**Test Execution:**
- Local: ~238 tests in ~13 seconds
- CI: phases run sequentially, total ~5 minutes including setup

## Regulatory Compliance

**IEC 62304 Requirements:**
- §5.5.2: Software unit verification
- §5.6.2: Software integration testing
- §5.7.2: Software system testing

**Audit Trail:**
- All test results stored in GitHub Actions artifacts
- Test execution history available via GitHub API
- Coverage reports for traceability

## Future Enhancements

1. **UI Testing:** Add Selenium/Playwright tests
2. **Performance Testing:** Add load/stress tests
3. **Security Scanning:** Integrate SAST/DAST tools
4. **Test Coverage:** Increase to >90%
5. **Parallel Execution:** Speed up CI with parallel jobs

#### Design Rationale

**GitHub Actions Integration**
- Chosen for seamless CI/CD integration
- No additional infrastructure required
- Free for public repositories
- Built-in artifact storage

**Hybrid Approach**
- Automated tests for fast feedback
- Manual tests for regulatory compliance
- Best of both worlds

**pytest Framework**
- Industry standard for Python testing
- Rich plugin ecosystem
- Excellent reporting capabilities
- Easy to learn and maintain


#### Alternatives Considered

**Jenkins/CircleCI**
- Rejected: More complex setup
- GitHub Actions sufficient for current needs

**Local File Storage for Results**
- Rejected: Not suitable for distributed teams
- GitHub artifacts provide better persistence

**unittest Framework**
- Rejected: pytest more feature-rich
- Better fixture management
- More readable test code


#### Technology Stack

- pytest - Test framework
- pytest-cov - Coverage reporting
- GitHub Actions - CI/CD platform
- JUnit XML - Test result format
- requests - HTTP client for GitHub API


#### Interfaces

**`parse_junit_xml(path) -> List[ExecutionResult]`** (`src/test_results/junit_parser.py`)
- Extracts TC ID from `compliantflow.id` property or test name regex
- Maps `<failure>` / `<skipped>` / pass to PASS / FAIL / SKIP
- Reads `compliantflow.links`, `.title`, `.reviewer`, `.review_date`, `.review_status`

**`ResultStore`** (`src/test_results/result_store.py`)
- `record_execution(tc_id, testing_status, ...)` — upserts one record
- `get(tc_id)`, `get_all(status_filter)`, `as_tc_items()` — reads

**`_TestResultsMixin`** (`src/compliantflow/mixins/test_results_mixin.py`)
- `import_test_results(results, tester, run_id, run_url, commit_sha)` — persists
  all results and recomputes `verification_status` on linked requirement items
- `get_test_result(tc_id)`, `get_all_test_results(status_filter)` — queries


#### Related Requirements

- SYS-020
- SYS-021
- SYS-022

</div>


---

## 3. Summary

### 3.1 Architecture Statistics

| Metric | Count |
|--------|-------|
| **Total Architecture Components** | 6 |
| **System Architecture** | 2 |
| **Data Architecture** | 1 |
| **UI Architecture** | 0 |
| **Integration Architecture** | 0 |

### 3.2 Component Status

| Status | Count |
|--------|-------|
| **Draft** | 2 |
| **Review** | 1 |
| **Approved** | 3 |

### 3.3 Technology Overview

This architecture specification documents the following key technologies:
- **CompliantFlow System Architecture**: See ARCH-001 for details
- **Data Model and Storage Architecture**: See ARCH-002 for details
- **Configuration-Driven Architecture**: See ARCH-003 for details
- **Test Automation and CI/CD Architecture**: See ARCH-006 for details

---

## 4. Compliance and Traceability

### 4.1 Requirements Traceability

This architecture specification satisfies the following system requirements:

- SYS-001
- SYS-002
- SYS-003
- SYS-004
- SYS-005
- SYS-020
- SYS-021
- SYS-022
- SYS-023
- SYS-028

### 4.2 IEC 62304 Compliance

This architecture documentation supports IEC 62304 compliance by providing:
- Clear system architecture definition (§5.3.1)
- Software item identification (§5.3.2)
- Interface specifications (§5.3.3)
- Design rationale and alternatives (§5.3.6)

---

## 5. Document Control

**Document Owner**: System Architecture Team  
**Last Updated**: 2025-12-21  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow from architecture specification items.*