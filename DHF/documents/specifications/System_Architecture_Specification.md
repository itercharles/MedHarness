# System Architecture Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SYSARCH-SPEC |
| **Version** | 1.1 |
| **Generated** | 2026-03-02 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. System Overview

CompliantFlow is a **web-based Design History File (DHF) management system** for medical device software development compliant with IEC 62304 and ISO 13485.

**System Purpose:** Enable development teams to manage requirements, traceability, testing, and regulatory documentation through a structured, auditable workflow.

---

## 2. System Architecture

### 2.1 Architecture Decision

**System Type:** Pure Software System
- Web-based Python application for DHF management
- Single software subsystem architecture

### 2.2 Technology Stack

**Core Technologies:**
- **Python 3.11+** - Application runtime
- **Streamlit** - Web framework and UI
- **NetworkX** - Graph analysis
- **Pydantic** - Data validation
- **Jinja2** - Template rendering
- **WeasyPrint** - PDF generation
- **YAML** - Data format
- **Git** - Version control

**Deployment:**
- Web browser (Chrome, Firefox, Safari)
- Python virtual environment
- File system for data storage

---

## 3. Data Management Architecture

### 3.1 Storage Strategy

**File-based with Git version control**

### 3.2 Data Structure

```
DHF/
├── items/                    # All DHF items
│   ├── 01_req_crs/          # Customer requirements
│   ├── 02_req_sys/          # System requirements
│   ├── 03_req_srs/          # Software requirements
│   ├── 04_req_sds/          # Design specifications
│   ├── 05_test_crs/         # Customer tests
│   ├── 06_test_sys/         # System tests
│   ├── 07_risk/             # Risk items
│   └── 08_defect/           # Defect items
├── config/
│   ├── project_config.yaml  # Document types, lifecycles
│   └── IEC_62304.yaml       # Compliance mapping
└── documents/
    ├── specifications/       # Generated documents
    └── procedures/          # Manual procedures
```

### 3.3 Design Rationale: File-Based vs Database

**Why File-Based (YAML + Git)?**

✅ **Traceability:** Each item = one file with unique ID  
✅ **Version Control:** Git provides complete audit trail (IEC 62304 §5.1.9)  
✅ **Human Readable:** YAML is text-based and easy to review  
✅ **Portability:** Entire DHF is a directory  
✅ **Simplicity:** No database server required  
✅ **Regulatory Compliance:** Supports IEC 62304 §5.1.4, §5.1.9, 21 CFR Part 11

**When Database Would Be Better:**
- Thousands of items (current: ~100s)
- Complex queries across items
- Multiple users editing simultaneously

**CompliantFlow's Scale:** 100-500 requirements, 2-10 users, simple parent-child links

---

## 4. Component Architecture

### 4.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CompliantFlow System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  User (Browser)  │◄────────┤  Streamlit UI    │          │
│  └──────────────────┘         └────────┬─────────┘          │
│                                         │                     │
│                              ┌──────────▼──────────┐         │
│                              │  CompliantFlowCore  │         │
│                              └──────────┬──────────┘         │
│                                         │                     │
│         ┌───────────────────────────────┼─────────────┐      │
│         │                               │             │      │
│  ┌──────▼────────┐  ┌──────────────────▼──┐  ┌───────▼────┐│
│  │ GraphEngine   │  │ DocumentGenerator   │  │ Lifecycle  ││
│  └──────┬────────┘  └──────────┬──────────┘  │ Methods    ││
│         │                      │              └───────┬────┘│
│         │                      │                      │      │
│  ┌──────▼──────────────────────▼──────────────────────▼────┐│
│  │              ItemLoader / ItemSaver                      ││
│  │              (YAML + Git)                                ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Component Descriptions

**CompliantFlowCore:**
- Central orchestrator
- Manages item lifecycle
- Coordinates graph, documents, workflow

**GraphEngine:**
- Builds traceability graph using NetworkX
- Analyzes dependencies
- Detects orphans and coverage gaps

**DocumentGenerator:**
- Renders Jinja2 templates
- Generates markdown specifications
- Converts to PDF using WeasyPrint

**LifecycleMethods:**
- Manages item lifecycle states
- Validates state transitions
- Enforces approval workflows

**ItemLoader/ItemSaver:**
- YAML file I/O operations
- Git commit automation
- Schema validation

### 4.3 Software Layered Architecture

**Layer 1: Presentation (Streamlit UI)**
- Universal page template
- Dynamic form generation
- Workflow transition UI
- Visualization components

**Layer 2: Business Logic**
- CompliantFlowCore: Central orchestrator
- GraphEngine: Traceability analysis
- LifecycleMethods: State management
- DocumentGenerator: Specification generation

**Layer 3: Data Access**
- ItemLoader: YAML file reading
- ItemSaver: YAML file writing + Git commits
- GitRepository: Version control operations

**Layer 4: Storage**
- File system (YAML files)
- Git repository

**Benefits:**
- Clear separation of concerns
- Independent testing of layers
- Easy to modify UI without changing logic
- Supports future database migration

### 4.4 Design Patterns

**Architectural Patterns:**
- **Layered Architecture**: Clear separation between UI, logic, and data
- **Repository Pattern**: ItemLoader/ItemSaver abstract file storage
- **Strategy Pattern**: Workflow validation criteria, policy validation rules

**Design Principles:**
- **Configuration-Driven Design**: Document types, workflows, policies in YAML
- **Fail-Fast Validation**: Configuration validated at startup
- **Separation of Concerns**: UI independent of storage, logic independent of UI

### 4.5 Data Flow

**Item Creation Flow:**
```
User Input (Streamlit)
  ↓
CompliantFlowCore.create_item()
  ↓
LifecycleMethods.get_initial_state()
  ↓
ItemSaver.save(item)
  ↓
YAML File + Git Commit
  ↓
GraphEngine.rebuild()
```

**Traceability Analysis Flow:**
```
User Request (Streamlit)
  ↓
CompliantFlowCore.get_traceability()
  ↓
GraphEngine.build_from_items()
  ↓
NetworkX Graph Operations
  ↓
Traceability Results
  ↓
Streamlit Visualization
```

**Document Generation Flow:**
```
User Request (Streamlit)
  ↓
DocumentGenerator.generate_specification()
  ↓
ItemLoader.load_all()
  ↓
Jinja2 Template Rendering
  ↓
Markdown → HTML → PDF
  ↓
Generated Document
```

---

## 5. Architecture Items

### 1. SYSARCH-001: Item Management Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 2. SYSARCH-002: Traceability Analysis Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 3. SYSARCH-003: Lifecycle Management Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 4. SYSARCH-004: Change Management Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 5. SYSARCH-005: Compliance Validation Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 6. SYSARCH-006: Document Generation Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 7. SYSARCH-007: Test Integration Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 8. SYSARCH-008: Web UI Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

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

### 9. SYSARCH-009: CLI Module

<div class="architecture-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Overview

Command-line interface module providing headless access to CompliantFlowCore
for CI/CD pipelines and scripted environments.

**Responsibilities**:
- Expose core DHF operations as CLI commands
- Parse command-line arguments and route to CompliantFlowCore methods
- Output machine-readable JSON to stdout for pipeline consumption
- Output human-readable diagnostics to stderr
- Return meaningful exit codes (0 = success, 1 = error/validation failure)

**Key Interfaces**:
- `CompliantFlowCore`: Single entry point for all business logic (shared with Web UI)
- `click`: Command-line argument parsing and help generation
- `python -m compliantflow`: Module entry point

**Implementation Notes**:
- Package location: `src/compliantflow/` (separate from `src/traceability/`)
- Uses `click` library (already installed as transitive dependency of streamlit)
- Stateless: each invocation creates a fresh CompliantFlowCore instance
- No shared state with the Streamlit UI; both call the same core independently
- stdout/stderr separation enables clean pipeline integration






</div>


---

## 6. Data Interfaces

### 6.1 ItemLoader

```python
class ItemLoader:
    def load_all() -> List[Item]
    def load_by_uid(uid: str) -> Optional[Item]
    def load_by_prefix(prefix: str) -> List[Item]
```

### 6.2 ItemSaver

```python
class ItemSaver:
    def save(item: Item, author: str) -> Path
    def delete(uid: str, author: str) -> bool
```

### 6.3 GitRepository

```python
class GitRepository:
    def commit(message: str, files: List[Path]) -> str
    def get_history(file_path: Path) -> List[Commit]
```

---

## 7. Technology Decisions

### 7.1 Why Python/Streamlit?
- Rapid development with quick UI prototyping
- Rich Python ecosystem for data processing
- Clear audit trail for medical device compliance

### 7.2 Why YAML Files?
- Human-readable for review and audit
- Git-friendly text format
- Supports IEC 62304 §5.1.4 (software item identification)

### 7.3 Why Git?
- IEC 62304 §5.1.9 (configuration management)
- Complete version history
- Industry standard for collaboration

---

## 8. Compliance Mapping

### 8.1 IEC 62304 Requirements

| IEC 62304 Section | CompliantFlow Implementation |
|-------------------|------------------------------|
| §5.1.4 Software Item Identification | YAML files with unique IDs |
| §5.1.9 Configuration Management | Git version control |
| §5.2 Software Requirements | SRS items in `DHF/items/03_req_srs/` |
| §5.3 Software Architecture | SWAD items |
| §5.4 Software Detailed Design | SWDD items |
| §9.7 Problem Resolution | Defect tracking system |

### 8.2 Requirements Traceability

This architecture specification satisfies the following system requirements:

*No requirement links defined*

---

## 9. Summary

### 9.1 Architecture Statistics

| Metric | Count |
|--------|-------|
| **Total Architecture Components** | 9 |
| **System Architecture** | 0 |
| **Data Architecture** | 0 |
| **UI Architecture** | 0 |
| **Integration Architecture** | 0 |

### 9.2 Component Status

| Status | Count |
|--------|-------|
| **Draft** | 0 |
| **Review** | 0 |
| **Approved** | 9 |

---

## 10. Future Considerations

### 10.1 Database Migration

To enable database migration, would need to:
1. Create abstract `ItemRepository` interface
2. Refactor `ItemLoader` + `ItemSaver` into `FileBasedRepository`
3. Create `DatabaseRepository` implementation
4. Update `CompliantFlowCore` to accept abstract repository

This is documented in the gap analysis but not currently implemented.

---

## 11. Document Control

**Document Owner**: System Architecture Team  
**Last Updated**: 2026-03-02  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow from architecture specification items.*