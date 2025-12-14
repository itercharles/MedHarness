# System Architecture Specification

## Overview

CompliantFlow is a configuration-driven requirements traceability system designed for IEC 62304 compliance. The system uses a universal framework approach where all item types (requirements, defects, releases, etc.) are managed through a single template driven by YAML configuration.

## Architecture Principles

### 1. Configuration-Driven Design
- **Single Source of Truth**: `DHF/config/project_config.yaml` defines all item types, lifecycles, and workflows
- **No Custom Code Per Type**: Adding new item types requires only configuration changes
- **Auto-Generated Pages**: Streamlit pages are generated from configuration

### 2. Universal Item Model
- All entities (requirements, defects, releases, CRs) use the same `Item` model
- Consistent storage format (YAML files in `DHF/items/`)
- Unified CRUD operations through `CompliantFlowCore`

### 3. Dynamic Workflow Engine
- Workflows defined in configuration, not code
- State machines with validation criteria
- Automatic enforcement of transition rules

## System Components

### Core Layer (`src/traceability/`)

#### CompliantFlowCore (401 lines)
**Purpose**: Central orchestrator for all traceability operations

**Responsibilities**:
- Load and manage project configuration
- Provide unified API for item management
- Coordinate graph engine and workflow engine
- Handle Git-based audit trail

**Key Methods**:
- `get_all_items()` - Retrieve all items
- `get_item_by_id(uid)` - Get specific item
- `create_item(doc_type, data)` - Create new item
- `update_item(uid, updates)` - Update existing item
- `transition_item(uid, to_state)` - Execute workflow transition

#### DynamicWorkflowEngine
**Purpose**: Execute lifecycle workflows defined in configuration

**Features**:
- State validation
- Transition criteria checking
- Automatic state updates
- Audit trail generation

#### GraphEngine
**Purpose**: Manage traceability relationships

**Features**:
- Build dependency graph from item links
- Detect orphan nodes
- Generate traceability matrices
- Validate coverage

### UI Layer (`src/pages/`)

#### Universal Page Template
**Purpose**: Single template serving all item types

**Features**:
- Dynamic table with filtering
- Detail panel with view/edit modes
- Workflow transition buttons
- Create new item forms
- Link management

**Auto-Generated Pages**:
- `4_Release.py` - Release management
- `5_Customer_Requirement.py` - Customer requirements (CRS)
- `6_System_Requirement.py` - System requirements (SYS)
- `7_Software_Design_Specification.py` - Design specs (SDS)
- `8_Defect.py` - Defect tracking
- `9_Change_Request.py` - Change requests

#### Page Generator (`generate_pages.py`)
**Purpose**: Auto-generate page files from configuration

**Usage**:
```bash
src/venv/bin/python3 src/generate_pages.py
```

### Data Layer (`DHF/`)

#### Configuration (`DHF/config/`)
- `project_config.yaml` - Master configuration
  - Doc type definitions
  - Lifecycle workflows
  - Properties and relations
  - UI settings

#### Items (`DHF/items/`)
Organized by type with numeric prefixes:
- `01_req_crs/` - Customer Requirements
- `02_req_sys/` - System Requirements
- `04_req_sds/` - Software Design Specifications
- `07_tc_sds/` - Test Cases
- `08_defect/` - Defects
- `09_cr/` - Change Requests
- `10_release/` - Releases

## Item Lifecycle Management

### Standard Approval Workflow
Used by: CRS, SYS, SDS

**States**:
1. `draft` - Initial state
2. `in_review` - Under review
3. `approved` - Approved and locked

**Transitions**:
- draft → in_review (requires: reviewer assigned)
- in_review → approved (requires: review complete)
- in_review → draft (reject)

### Defect Workflow
**States**:
1. `open` - Newly reported
2. `in_progress` - Being worked on
3. `resolved` - Fix implemented
4. `verified` - Fix verified
5. `closed` - Completed
6. `reopened` - Reopened after closure

### Change Request Workflow
**States**:
1. `submitted` - Initial submission
2. `under_review` - Being reviewed
3. `approved` - Approved for implementation
4. `rejected` - Rejected
5. `in_progress` - Being implemented
6. `completed` - Implementation complete
7. `cancelled` - Cancelled

### Release Workflow
**States**:
1. `planning` - Planning phase
2. `developing` - Development in progress
3. `testing` - Testing phase
4. `released` - Released to production

## Data Model

### Item Model
```python
class Item:
    uid: str                    # Unique identifier (e.g., "SYS-001")
    title: str                  # Human-readable title
    content: str                # Main content/description
    status: str                 # Current lifecycle state
    links: List[str]            # Links to other items
    verification_status: str    # PASS, FAIL, PENDING
    # ... additional properties defined per doc type
```

### Configuration Model
```python
class DocTypeConfig:
    code: str                   # Type code (e.g., "SYS")
    name: str                   # Display name
    prefix: str                 # ID prefix (e.g., "SYS-")
    properties: List[str]       # Available properties
    icon: str                   # UI icon
    page_enabled: bool          # Show in sidebar
    page_number: int            # Sidebar position
    lifecycle: LifecycleConfig  # Workflow definition
```

## Traceability Graph

### Relationship Types
- **verifies**: Test cases verify requirements
- **implements**: Design specs implement requirements
- **links**: Generic relationship

### Coverage Analysis
- Requirement → Design → Test coverage
- Orphan node detection
- Bidirectional link validation

## Compliance Features

### IEC 62304 §9.7 - Problem Resolution
- Defect tracking with full lifecycle
- Root cause analysis required
- Resolution verification
- Complete audit trail

### Audit Trail
- Git-based version control
- All changes tracked with author and timestamp
- Immutable history
- Compliance-ready reports

## Extension Points

### Adding New Item Types

1. **Update Configuration**:
```yaml
doc_types:
  - code: NEWTYPE
    name: "New Type"
    prefix: "NEW-"
    properties: ["id", "title", "content", "status", "links"]
    icon: "🆕"
    page_enabled: true
    page_number: 11
    lifecycle:
      states:
        - {id: draft, label: "Draft", is_initial: true}
        - {id: approved, label: "Approved"}
      transitions:
        - {from: draft, to: approved, label: "Approve"}
```

2. **Generate Pages**:
```bash
src/venv/bin/python3 src/generate_pages.py
```

3. **Create Directory**:
```bash
mkdir -p DHF/items/11_newtype
```

4. **Add Sample Items** - Create YAML files in the new directory

**That's it!** No code changes needed.

## Performance Considerations

- **Lazy Loading**: Items loaded on demand
- **Caching**: Configuration cached at startup
- **Incremental Updates**: Only modified items reloaded
- **Git Efficiency**: Atomic commits per operation

## Security

- **File-Based Storage**: No database vulnerabilities
- **Git Audit Trail**: Tamper-evident history
- **No Authentication**: Designed for trusted environments
- **Local Deployment**: No network exposure by default

## Future Enhancements

- [ ] Real-time collaboration
- [ ] Advanced search and filtering
- [ ] Custom report templates
- [ ] API for external integrations
- [ ] Automated test execution
- [ ] Release validation automation
