# DHF Utils — Functional Requirements

Requirements for the `DHF/utils/` data-layer package and CLI.

---

## REQ-001: Item Persistence and Versioning
*Derived from SYS-001 (Object Management)*

Software shall persist DHF items to file storage with complete version history.

**Behavior:**
- Store each item as a separate YAML file with a unique identifier
- Automatically generate unique IDs in format `{PREFIX}-{NUMBER}` (e.g. `SRS-001`)
- Use sequential numbering based on existing items (max + 1)
- Prevent duplicate IDs by checking existing items before creation
- Maintain complete change history with author and timestamp
- Support atomic read and write operations
- Validate item schema before persistence

**Acceptance Criteria:**
- Items can be saved and retrieved by ID
- IDs are automatically generated and unique
- Change history includes author, timestamp, and changes made
- Invalid items are rejected with clear error messages

---

## REQ-002: Traceability Graph Construction
*Derived from SYS-003 (Visual Traceability)*

Software shall build a directed graph representing traceability relationships between items.

**Behavior:**
- Create graph nodes for each DHF item
- Create graph edges from item link fields (`derives_from`, `implements`, `verifies`, `satisfies`)
- Support bidirectional traversal (upstream and downstream)
- Update graph when items are added, modified, or deleted

**Acceptance Criteria:**
- Graph contains all items as nodes
- Edges correctly represent configured relationship types
- Can find all parent items (upstream traversal)
- Can find all child items (downstream traversal)

---

## REQ-003: Orphan Item Detection
*Derived from SYS-004 (Orphan Reporting)*

Software shall identify items that lack required traceability links.

**Behavior:**
- Detect items with no incoming links (missing parents)
- Detect items with no outgoing links (missing children)
- Exclude configured root types (UC, CRS) from orphan detection
- Group orphans by document type

**Acceptance Criteria:**
- Orphan detection completes in < 1 second for 1000 items
- Root types are not flagged as orphans
- Orphans are correctly grouped by document type

---

## REQ-004: Coverage Metrics Calculation
*Derived from SYS-003 (Visual Traceability)*

Software shall calculate verification coverage from source items to test items.

**Behavior:**
- Identify source items (requirements)
- Find linked verification items (tests)
- Calculate coverage percentage: `(verified items / total items) × 100`
- Report items without verification links

**Acceptance Criteria:**
- Coverage calculation is accurate to 2 decimal places
- Unverified items are correctly identified

---

## REQ-005: Policy-Based Compliance Validation
*Derived from SYS-005 (Compliance Assessment)*

Software shall validate the DHF against configurable compliance policies.

**Behavior:**
- Load policy definitions from configuration (YAML governance files)
- Execute validation rules against DHF items
- Calculate compliance score per policy group
- Collect evidence for each validation result

**Acceptance Criteria:**
- All configured policies are executed
- Validation completes in < 5 seconds for 1000 items
- Compliance score is the percentage of passed rules
- Evidence includes specific items and rule results

---

## REQ-006: Configurable Workflow Engine
*Derived from SYS-010 (Object Workflow Management)*

Software shall enforce configurable lifecycle workflows for explicit-lifecycle items.

**Scope:** Applies only to **CR, REL, and DEF**. Requirement items (UC, CRS, SYS, SRS,
SWDD, SYSARCH, SOUP, RISK, RCM) use the GitOps approval model — no status field, no
transitions.

**Behavior:**
- Load workflow definitions from doc-type configuration
- Validate state transitions against workflow rules
- Execute transition criteria before allowing transitions
- Support per-document-type workflow configurations

**Acceptance Criteria:**
- Invalid transitions are blocked with a clear error message
- Transition criteria are executed in order
- Failed criteria prevent the transition
- Workflow configuration errors are detected at startup

---

## REQ-007: Template-Based Document Generation
*DHF utils standalone requirement (SYS-021 removed from product DHF by CR-022)*

Software shall generate specification documents from Jinja2 templates.

**Behavior:**
- Load document templates from configured directory
- Gather item data for template context
- Render templates with item data to produce Markdown
- Export Markdown to PDF via WeasyPrint
- Track document versions automatically

**Acceptance Criteria:**
- Generated documents include all configured items
- Document version increments on regeneration
- PDF export produces a well-formatted document

---

## REQ-008: Test Result Integration
*Derived from SYS-033 (External Test Result Integration via CLI)*

Software shall retrieve and persist test results from any CI/CD pipeline into the DHF,
linking each result to the requirement items it verifies.

**Mechanism:**
- Test functions embed metadata in docstrings using `@`-tags:
  - `@test_id: TC-SYS-001-001` (optional; inferred from function name if absent)
  - `@links: SYS-001, SYS-002` (requirement items this TC verifies)
  - `@reviewer:`, `@review_status:`, `@review_date:` (optional review metadata)
- A pytest autouse fixture (`tests/conftest.py`) injects these as `compliantflow.*`
  properties into the JUnit XML output
- `compliantflow test import <file>` parses JUnit XML and persists one record per TC
  in `DHF/test-results/results.yaml`
- After import, `verification_status` is recomputed on linked requirement items:
  `verified` / `failed` / `not_verified`

**CLI Commands:**
- `test import` — parse JUnit XML and persist results
- `test status <TC-ID>` — retrieve stored record as JSON
- `test list [--status PASS|FAIL|SKIP]` — list stored TC records
- `test pull [--run-id RUN_ID]` — fetch results from GitHub Actions artifacts

**Acceptance Criteria:**
- All `compliantflow.*` properties are extracted and stored correctly
- PASS / FAIL / SKIP statuses are correctly parsed
- Tests with no recognisable TC ID are silently skipped
- Linked requirement items have `verification_status` updated after import

---

## REQ-009: Configurable Document Type Definitions
*Derived from SYS-001 (Object Management)*

Software shall load and validate document type definitions from configuration at startup.

**Behavior:**
- Load doc type schemas from `DHF/config/doc_types/*.yaml` + `DHF/config/global.yaml`
- Validate required fields (code, prefix, directory, properties)
- Support dynamic field definitions per document type
- Load per-type lifecycle configurations
- Raise `ValidationError` on unknown fields in loaded YAML files

**Acceptance Criteria:**
- Invalid configuration fails at startup with a clear error
- All document types have required fields
- Unknown item fields are rejected with field name and doc type in the error message

---

## REQ-010: Component Boundary Isolation
*Derived from SYS-034 (Component Boundary Isolation)*

The `src/compliantflow/` analysis engine shall not directly import DHF I/O modules
outside the adapter boundary.

**Prohibited imports** (for all files except `src/compliantflow/adapters/local.py`):
- `utils.repository.*`
- `utils.result_store`
- `utils.junit_parser`
- `utils.document_generation`

**Permitted imports** (shared data types, no I/O side effects):
- `utils.models.*`
- `utils.exceptions`

All DHF I/O operations shall be routed through the `DHFAdapter` protocol
(`src/compliantflow/adapters/protocol.py`).

**Verification:** Automated import boundary scan in CI (`DHF/utils/tests/test_srs_034_boundary.py`).
