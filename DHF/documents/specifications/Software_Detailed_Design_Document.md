# Software Detailed Design Document Specification

---

**Document Metadata**

| Field | Value |
|-------|-------|
| **Document ID** | SWDD-SPEC |
| **Version** | 1.1 |
| **Generated** | 2026-03-02 |
| **Status** | Draft |
| **Project** | CompliantFlow Project |

---

## 1. Introduction

This document specifies the Software Detailed Design Document for CompliantFlow Project. This specification is part of the Design History File (DHF) and provides traceability for regulatory compliance.

### 1.1 Purpose

This document provides a comprehensive list of all Software Detailed Design Documents, including their current status, content, and traceability links to related items.

### 1.2 Scope

This specification covers all Software Detailed Design Documents defined in the CompliantFlow system as of 2026-03-02.

---

## 2. Requirements

### 1. SWDD-001: Item Loading from YAML

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for loading DHF items from YAML files with schema validation.

**Component Structure**:
- ItemLoader: Main loading class
- YAMLParser: Parse YAML files
- SchemaValidator: Validate against Pydantic models

**Algorithm**:
1. Scan configured directories for YAML files
2. For each file: parse YAML content
3. Validate against item type schema
4. Collect valid items into list
5. Log and skip invalid files

**Key Interfaces**:
```python
class ItemLoader:
    def load_all() -> List[Item]
    def load_by_id(uid: str) -> Optional[Item]
    def load_by_type(doc_type: str) -> List[Item]
```

**Design Patterns**:
- Repository pattern for data access
- Factory pattern for item creation

**Error Handling**:
- Skip malformed YAML files with logging
- Don't fail entire load on single file error

**Complexity**: O(N) where N = number of files



</div>

### 2. SWDD-002: Item Persistence with Git

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for saving DHF items to YAML files with Git commit tracking.

**Component Structure**:
- ItemSaver: Main saving class
- YAMLSerializer: Convert items to YAML
- GitCommitter: Create Git commits

**Algorithm**:
1. Validate item against Pydantic schema
2. Serialize item to YAML format
3. Write to file atomically (temp file + rename)
4. Create Git commit with item ID and author
5. Rollback file on Git failure

**Key Interfaces**:
```python
class ItemSaver:
    def save(item: Item, author: str) -> Path
    def delete(uid: str, author: str) -> bool
```

**Design Patterns**:
- Transaction pattern for atomic operations
- Command pattern for Git operations

**Error Handling**:
- Rollback file write if Git commit fails
- Validate before save to prevent corruption

**Complexity**: O(1) per item



</div>

### 3. SWDD-003: Graph Construction

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for building traceability graph from DHF items.

**Component Structure**:
- GraphBuilder: Construct NetworkX graph
- NodeFactory: Create graph nodes
- EdgeFactory: Create graph edges

**Algorithm**:
1. Create empty NetworkX DiGraph
2. For each item: add node with attributes (ID, type, status, title)
3. For each item: parse link fields (derives_from, implements, verifies)
4. For each link: add directed edge
5. Return constructed graph

**Key Interfaces**:
```python
class GraphEngine:
    def build_from_items(items: List[Item]) -> nx.DiGraph
    def rebuild() -> None
    def get_graph() -> nx.DiGraph
```

**Design Patterns**:
- Builder pattern for graph construction
- Singleton pattern for graph instance

**Data Structures**:
- NetworkX DiGraph with node/edge attributes
- In-memory graph for fast queries

**Complexity**: O(N + E) where N = nodes, E = edges



</div>

### 4. SWDD-004: Orphan Detection

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for detecting items without required traceability links.

**Component Structure**:
- OrphanDetector: Main detection logic
- NodeFilter: Filter nodes by criteria
- OrphanClassifier: Classify orphan types

**Algorithm**:
1. Filter graph nodes by document type
2. Exclude root types (UC, CRS) from analysis
3. Find nodes with in_degree = 0 (missing parents)
4. Find nodes with out_degree = 0 (missing children)
5. Group orphans by type and return

**Key Interfaces**:
```python
class GraphEngine:
    def find_orphans(doc_type: str = None) -> List[dict]
    def find_source_orphans() -> List[str]
    def find_target_orphans() -> List[str]
```

**Design Patterns**:
- Strategy pattern for different orphan types
- Filter pattern for node selection

**Orphan Types**:
- Source orphans: No incoming links (missing parents)
- Target orphans: No outgoing links (missing children)

**Complexity**: O(N) where N = nodes of specified type



</div>

### 5. SWDD-005: Coverage Calculation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for calculating verification coverage from source to test items.

**Component Structure**:
- CoverageAnalyzer: Main analysis logic
- PathFinder: Find paths in graph
- CoverageCalculator: Compute percentages

**Algorithm**:
1. Get all source items (e.g., requirements)
2. For each source: traverse graph to find verification items
3. Mark source as verified if path to test exists
4. Calculate coverage: (verified_count / total_count) × 100
5. Return coverage report with unverified items

**Key Interfaces**:
```python
class CoverageAnalyzer:
    def calculate_coverage(source_type: str, target_type: str) -> dict
    def get_uncovered_items(source_type: str) -> List[str]
    def get_coverage_report() -> CoverageReport
```

**Design Patterns**:
- Visitor pattern for graph traversal
- Strategy pattern for different coverage types

**Coverage Metrics**:
- Percentage: (verified / total) × 100
- Uncovered items list
- Coverage by document type

**Complexity**: O(N × D) where N = source items, D = graph depth



</div>

### 6. SWDD-006: Policy Validation Execution

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for executing compliance policy validation rules.

**Component Structure**:
- PolicyEngine: Main validation orchestrator
- RuleExecutor: Execute individual rules
- EvidenceCollector: Gather validation evidence
- ScoreCalculator: Compute compliance scores

**Algorithm**:
1. Load policy group from YAML configuration
2. For each validation rule in policy:
   a. Execute rule against DHF items
   b. Collect pass/fail result with evidence
3. Calculate compliance score: (passed / total) × 100
4. Return ValidationResults with details

**Key Interfaces**:
```python
class PolicyEngine:
    def execute_validation(policy_name: str) -> ValidationResults
    def validate_all() -> dict
    def get_policy_score(policy_name: str) -> float

class ValidationRule(ABC):
    @abstractmethod
    def validate(items: List[Item]) -> (bool, str)
```

**Design Patterns**:
- Strategy pattern for validation rules
- Template method for validation flow
- Composite pattern for rule groups

**Rule Types**:
- Coverage rules: Check source items have verification
- Orphan rules: Check items have required links
- Status rules: Check items in required states

**Complexity**: O(R × I) where R = rules, I = items per rule



</div>

### 7. SWDD-007: Change Request Management

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for managing change request lifecycle.

**Component Structure**:
- ChangeRequestManager: CR lifecycle management
- CRIDGenerator: Generate unique CR IDs
- CRValidator: Validate CR data
- CRPersister: Save CR to YAML

**Algorithm**:
1. Generate unique CR ID (sequential: CR-001, CR-002, ...)
2. Validate CR input data (title, description, affected items)
3. Create CR YAML file in DHF/items/09_cr/
4. Initialize CR with 'draft' status
5. Create Git commit

**Key Interfaces**:
```python
class ChangeRequestManager:
    def create_cr(data: dict, author: str) -> CR
    def update_cr(uid: str, data: dict) -> CR
    def approve_cr(uid: str, approver: str) -> CR
    def get_cr(uid: str) -> CR
```

**Design Patterns**:
- State pattern for CR lifecycle
- Factory pattern for CR creation
- Repository pattern for CR storage

**CR Lifecycle States**:
- draft → review → approved → implemented → closed

**Complexity**: O(1) per operation



</div>

### 8. SWDD-008: PR-CR Linking and Impact Tracking

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for linking pull requests to change requests and tracking impacted objects.

**Component Structure**:
- PRLinker: Link PRs to CRs
- CRReferenceParser: Parse CR-XXX from PR description
- ImpactAnalyzer: Identify affected items from PR files
- CRUpdater: Update CR with PR information

**Algorithm**:
1. Parse PR description with regex for CR-XXX pattern
2. Validate referenced CR exists and status is editable
3. Extract affected items from PR file changes:
   a. Get list of changed files from PR
   b. Map file paths to item IDs (e.g., DHF/items/03_req_srs/SRS-001.yaml → SRS-001)
4. Update CR YAML file:
   a. Add PR info (number, URL, title) to implementation_prs list
   b. Add affected items to affected_items list
5. Commit CR file changes

**Key Interfaces**:
```python
class PRLinker:
    def link_pr_to_cr(pr_number: int, cr_id: str) -> None
    def extract_cr_reference(pr_description: str) -> Optional[str]
    def get_affected_items(pr_files: List[str]) -> List[str]

class ImpactAnalyzer:
    def analyze_impact(affected_items: List[str]) -> ImpactReport
    def get_downstream_items(item_ids: List[str]) -> Set[str]
```

**Design Patterns**:
- Observer pattern for PR events
- Strategy pattern for impact analysis
- Adapter pattern for GitHub API

**Error Handling**:
- Reject if CR not found
- Reject if CR status not editable
- Log warnings for unrecognized file paths

**Complexity**: O(F) where F = files in PR



</div>

### 9. SWDD-009: State Transition Validation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for validating item lifecycle state transitions.

**Component Structure**:
- WorkflowEngine: Main workflow orchestrator
- TransitionValidator: Validate transitions
- CriteriaExecutor: Execute validation criteria
- WorkflowLoader: Load workflow from configuration

**Algorithm**:
1. Load workflow configuration for item's document type
2. Check if transition exists (from_state → to_state)
3. Execute transition criteria in order:
   a. Field validation (e.g., field_not_empty)
   b. Manual verification checks
   c. Linked item status checks
4. Collect validation errors
5. Return (is_valid, error_messages)

**Key Interfaces**:
```python
class WorkflowEngine:
    def validate_transition(item: Item, to_state: str) -> (bool, List[str])
    def execute_transition(item: Item, to_state: str, author: str) -> Item
    def get_available_transitions(item: Item) -> List[str]

class CriteriaExecutor:
    def execute(criteria: dict, item: Item) -> (bool, str)
```

**Design Patterns**:
- State pattern for lifecycle management
- Strategy pattern for validation criteria
- Chain of responsibility for criteria execution

**Criteria Types**:
- field_not_empty: Check required fields populated
- manual_verification: Require manual approval
- linked_items_status: Check linked items in required states

**Error Handling**:
- Fail-fast: Stop on first failed criterion
- Clear error messages for each failure

**Complexity**: O(C) where C = number of criteria



</div>

### 10. SWDD-010: Template Rendering

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for rendering Jinja2 templates with DHF item data.

**Component Structure**:
- TemplateRenderer: Main rendering orchestrator
- TemplateLoader: Load templates from directory
- ContextBuilder: Build template context
- MarkdownGenerator: Generate markdown output

**Algorithm**:
1. Load Jinja2 template from configured path
2. Gather all items for document type
3. Build template context:
   a. Items list
   b. Metadata (version, date, status)
   c. Configuration data
   d. Traceability data (if needed)
4. Render template with Jinja2 engine
5. Return generated markdown

**Key Interfaces**:
```python
class DocumentGenerator:
    def generate_specification(doc_type: str) -> Path
    def render_template(template: str, context: dict) -> str

class TemplateRenderer:
    def load_template(name: str) -> Template
    def render(template: Template, context: dict) -> str
```

**Design Patterns**:
- Template method for generation flow
- Builder pattern for context creation
- Strategy pattern for different document types

**Template Context Structure**:
- items: List[Item]
- metadata: dict (version, date, author, status)
- config: dict (project settings)
- traceability: dict (graph data if needed)

**Complexity**: O(N) where N = items to include



</div>

### 11. SWDD-011: PDF Export

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for exporting markdown documents to PDF format.

**Component Structure**:
- PDFExporter: Main export orchestrator
- MarkdownConverter: Convert markdown to HTML
- CSSLoader: Load PDF styling
- PDFGenerator: Generate PDF with WeasyPrint

**Algorithm**:
1. Convert markdown to HTML using Python-Markdown
2. Load CSS stylesheet for PDF styling
3. Apply CSS to HTML content
4. Generate PDF with WeasyPrint library
5. Write PDF to output path
6. Return output path

**Key Interfaces**:
```python
class PDFExporter:
    def export_to_pdf(markdown: str, output: Path) -> None
    def convert_to_html(markdown: str) -> str
    def apply_styling(html: str, css: str) -> str
```

**Design Patterns**:
- Pipeline pattern for conversion flow
- Strategy pattern for different output formats

**Styling**:
- CSS for page layout (margins, headers, footers)
- Typography (fonts, sizes, line heights)
- Table styling
- Code block formatting

**Complexity**: O(M) where M = markdown content length



</div>

### 12. SWDD-012: Test Result Parsing and Import

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design for importing test results from any CI/CD pipeline via JUnit XML.

**Component Structure**:
- `parse_junit_xml` (`src/test_results/junit_parser.py`): parse JUnit XML into ExecutionResult list
- `ResultStore` (`src/test_results/result_store.py`): persist one record per TC in results.yaml
- `_TestResultsMixin` (`src/compliantflow/mixins/test_results_mixin.py`): orchestrate import and
  recompute verification_status on linked requirement items

**Algorithm**:
1. Parse JUnit XML file (framework-agnostic; any framework producing JUnit XML is supported)
2. For each `<testcase>` element:
   a. Extract TC ID: from `compliantflow.id` property first; fall back to regex on test name
      (e.g. `test_TC_SYS_001_001_*` → `TC-SYS-001-001`); skip if no ID found
   b. Determine status: `<failure>` → FAIL, `<skipped>` → SKIP, else → PASS
   c. Extract `compliantflow.links`, `.title`, `.reviewer`, `.review_date`, `.review_status`
3. Upsert each result in `DHF/test-results/results.yaml` via `ResultStore.record_execution()`
4. Collect all requirement IDs linked by the imported TCs
5. For each linked requirement item with `has_verification: true`:
   - All linked TCs PASS → `verification_status: verified`
   - Any linked TC FAIL → `verification_status: failed`
   - No results yet → `verification_status: not_verified`

**Key Interfaces**:
```python
@dataclass
class ExecutionResult:
    id: str               # TC-SYS-001-001
    testing_status: str   # PASS / FAIL / SKIP
    links: List[str]      # from compliantflow.links property
    title: str
    reviewer: str
    review_date: str
    review_status: str
    error_message: Optional[str]

def parse_junit_xml(path: Path) -> List[ExecutionResult]: ...

class ResultStore:
    def record_execution(self, tc_id, testing_status, tester,
                         run_id, run_url, commit_sha, links, title,
                         reviewer, review_date, review_status) -> None: ...
    def get(self, tc_id) -> dict | None: ...
    def get_all(self, status_filter=None) -> dict: ...
```

**pytest adapter** (`tests/conftest.py` + `tests/utils/docstring_parser.py`):
- autouse fixture reads `@`-tags from test docstrings and calls `record_property()`
  to inject `compliantflow.*` properties into the JUnit XML output
- Helper functions in `docstring_parser.py` are also used by SRS unit tests directly

**Supported Input**:
- JUnit XML only (framework-agnostic boundary; `src/` has no pytest dependency)

**Complexity**: O(T) where T = number of test cases in XML



</div>

### 13. SWDD-013: CLI Implementation

<div class="requirement-section">

**Status**: <span class="status-approved">APPROVED</span>  

#### Description

Detailed design of the `compliantflow` CLI package.

**Package structure**:
```
src/compliantflow/
  __init__.py       # package marker
  __main__.py       # entry: from .cli import main; main()
  cli.py            # all click commands
```

**Click command hierarchy**:
```
main (group, --dhf option)
  validate
  item (group)
    list (--type, --status, --search)
    get <ITEM_ID>
  cr (group)
    check-status <CR_ID>
    update <CR_ID> (--item repeatable, --pr-number, --pr-url, --pr-title)
  traceability (group)
    neighbors <ITEM_ID>
```

**DHF path resolution** (in order):
1. `--dhf` CLI option if provided
2. `COMPLIANTFLOW_DHF` environment variable
3. Default: `<repo_root>/DHF` where repo_root = parent of `src/`

**Exit code contract**:
- 0: success
- 1: business error (item not found, CR stable, validation failed)
- 2: click usage error (wrong arguments)

**Core instantiation**:
```python
core = CompliantFlowCore(repo_root=dhf_path.parent)
```
One instance per CLI invocation; `auto_commit=False` (CI manages git).



</div>


---

## 3. Summary

### 3.1 Statistics

| Metric | Count |
|--------|-------|
| **Total Requirements** | 13 |
| **Approved** | 13 |
| **Draft** | 0 |
| **Retired** | 0 |

### 3.2 Approval Status

**Approval Rate**: 100.0% (13/13)

---

## 4. Document Control

**Document Owner**: Quality Assurance  
**Last Updated**: 2026-03-02  
**Next Review**: TBD

---

*This document was automatically generated by CompliantFlow.*
