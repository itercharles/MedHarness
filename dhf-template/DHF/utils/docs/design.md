# DHF Utils — Software Detailed Design

Detailed design specifications for `DHF/utils/` modules.

---

## DESIGN-001: Item Loading from YAML
*Implements REQ-001, REQ-009*

**Component:** `DHF/utils/repository/loader.py` — `ItemLoader`

**Algorithm:**
1. Scan configured `DHF/items/<directory>/` for YAML files
2. For each file: parse YAML content
3. Build allowed-field set per doc type: `_SYSTEM_FIELDS` + declared `properties` + lifecycle-derived fields
4. Reject files with unknown fields (`ValidationError`)
5. Validate against `Item` Pydantic model
6. Return collected `List[Item]`

**Key Interface:**
```python
class ItemLoader:
    def load_all(self) -> List[Item]
    def load_by_uid(self, uid: str) -> Optional[Item]
```

**Error Handling:** Unknown fields → `ValidationError` with field name + doc type.

**Complexity:** O(N) where N = number of YAML files.

---

## DESIGN-002: Item Persistence with Git
*Implements REQ-001*

**Component:** `DHF/utils/repository/saver.py` — `ItemSaver`

**Algorithm:**
1. Validate item against `Item` Pydantic schema
2. Serialize to YAML (atomic write: temp file + rename)
3. Create Git commit with item ID and author
4. Rollback file on Git failure

**Key Interface:**
```python
class ItemSaver:
    def save(self, item: Item, author: str, cr_id: Optional[str]) -> Path
    def delete(self, uid: str, author: Optional[str]) -> bool
```

**Transaction pattern:** File write is rolled back if the Git commit fails.

---

## DESIGN-003: Graph Construction
*Implements REQ-002*

**Component:** `src/compliantflow/traceability/graph/engine.py` — `GraphEngine`

**Algorithm:**
1. Create empty NetworkX `DiGraph`
2. For each item: add node with attributes (id, doc_type, status, title)
3. For each item: parse `all_linked_uids` (computed `@property` on `Item`)
4. Add directed edge **child → parent** for each link
5. Store graph for fast in-memory queries

**Key Interface:**
```python
class GraphEngine:
    def build_from_items(self, items: List[Item]) -> None
    def get_graph(self) -> nx.DiGraph
```

**Edge Semantics:**
- `nx.descendants(G, id)` = business **upstream** (parents, grandparents)
- `nx.ancestors(G, id)` = business **downstream** (children, grandchildren)

---

## DESIGN-004: Orphan Detection
*Implements REQ-003*

**Algorithm:**
1. Filter graph nodes by document type (exclude root types UC, CRS)
2. Source orphans: nodes with `in_degree = 0` (no parent links)
3. Target orphans: nodes with `out_degree = 0` (no child links)
4. Return grouped by type

**Complexity:** O(N) where N = number of nodes.

---

## DESIGN-005: Coverage Calculation
*Implements REQ-004*

**Algorithm:**
1. Get all source items (requirements with `has_verification: true`)
2. For each source: check if a path exists to a TC item via graph traversal
3. Compute: `coverage = (verified_count / total_count) × 100`
4. Return report with unverified items list

---

## DESIGN-006: Policy Validation Execution
*Implements REQ-005*

**Component:** `src/compliantflow/traceability/compliance/`

**Algorithm:**
1. Load policy group from `DHF/governance/<policy>.yaml`
2. For each validation rule: execute against DHF items; collect pass/fail + evidence
3. Score: `(passed / total) × 100`
4. Return `ComplianceReport` with per-rule results

**Rule Types:**
- `coverage` — check source items have verification links
- `orphan` — check items have required links
- `status` — check items are in required states
- `field_presence` — check required fields are populated

---

## DESIGN-007: State Transition Validation (CR/REL/DEF only)
*Implements REQ-006*

**Component:** `src/compliantflow/traceability/lifecycle_methods.py`

**Scope:** Applies ONLY to CR, REL, and DEF. Requirement items have no lifecycle config
and return `[]` from `get_available_transitions()`.

**Algorithm:**
1. Load lifecycle config from doc-type YAML
2. Check transition exists (`from_state → to_state`)
3. Execute criteria in order:
   - `field_not_empty` — required field populated
   - `manual_verification` — manual approval gate
   - `linked_items_status` — linked items in required states
4. Fail-fast on first failed criterion; return `(False, [error_messages])`
5. On success: write `status: <to_state>` to item YAML

**Criteria Execution Order:** Criteria are executed sequentially; first failure stops the chain.

---

## DESIGN-008: Template Rendering
*Implements REQ-007*

**Component:** `DHF/utils/document_generation.py` — `DocumentGenerator`

**Algorithm:**
1. Load Jinja2 template from `DHF/documents/specifications/templates/<doc_type>.md.j2`
2. Build context: items list, metadata (version, date), config data
3. Render with Jinja2 engine → Markdown string
4. Write to `DHF/documents/specifications/<DocType>_Specification.md`
5. Extract version from existing doc header; increment for new version

**Key Interface:**
```python
class DocumentGenerator:
    def generate_markdown_spec(self, doc_type_code: str, ...) -> Tuple[str, Path]
    def export_static_doc_to_pdf(self, doc_type_code: str, ...) -> Path
```

---

## DESIGN-009: PDF Export
*Implements REQ-007*

**Component:** `DHF/utils/document_generation.py` (PDF export path)

**Algorithm:**
1. Convert Markdown to HTML using `Python-Markdown`
2. Load CSS stylesheet for PDF styling
3. Apply CSS to HTML
4. Generate PDF with WeasyPrint
5. Write to `DHF/documents/specifications/<DocType>_Specification.pdf`

---

## DESIGN-010: Test Result Parsing and Import
*Implements REQ-008*

**Components:**
- `DHF/utils/junit_parser.py` — `parse_junit_xml()`, `ExecutionResult`
- `DHF/utils/result_store.py` — `ResultStore`

**Algorithm:**
1. Parse JUnit XML (framework-agnostic; any JUnit-compatible output works)
2. For each `<testcase>`:
   - TC ID: from `compliantflow.id` property, or regex on test name (`test_TC_SYS_001_001_*`)
   - Status: `<failure>` → FAIL, `<skipped>` → SKIP, else PASS
   - Links: from `compliantflow.links` (comma-separated requirement IDs)
   - Skip if no TC ID found
3. Upsert via `ResultStore.record_execution()` into `results.yaml`
4. Recompute `verification_status` on linked requirement items

**Key Interfaces:**
```python
@dataclass
class ExecutionResult:
    id: str                    # e.g. TC-SYS-001-001
    testing_status: str        # PASS / FAIL / SKIP
    links: List[str]           # requirement IDs
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
    def get(self, tc_id: str) -> Optional[dict]: ...
    def get_all(self, status_filter: Optional[str] = None) -> dict: ...
    def as_tc_items(self) -> List[dict]: ...
```

**pytest Adapter** (in `tests/`):
The pytest-specific adapter lives in `tests/conftest.py` and
`tests/utils/docstring_parser.py`. It reads `@`-tags from test docstrings and injects
them as `compliantflow.*` JUnit XML properties. `DHF/utils/` has no pytest dependency.

---

## DESIGN-011: Config-Driven Document Type Schema
*Implements REQ-009*

**Component:** `DHF/utils/models/config.py` — `ProjectConfig`, `DocTypeConfig`

**Algorithm:**
1. Load `DHF/config/global.yaml` + each `DHF/config/doc_types/*.yaml`
2. Parse into `ProjectConfig` Pydantic model (strict validation)
3. Build per-doc-type allowed-field set:
   - `_SYSTEM_FIELDS`: `id`, `doc_type`, `status`, `history`, `reviewer`, `review_date`
   - Declared `properties` from `DocTypeConfig.properties`
   - Lifecycle-derived fields: `{to_state}_by` / `{to_state}_date` per transition
   - `verification_status` when `has_verification: true`
4. On item load: validate YAML keys against allowed set; raise `ValidationError` on unknowns

**Key Interfaces:**
```python
class ProjectConfig(BaseModel):
    doc_types: List[DocTypeConfig]
    test_integration: dict
    document_specifications: dict

    @classmethod
    def load(cls, config_dir: Path) -> "ProjectConfig": ...
    def get_doc_type(self, code: str) -> Optional[DocTypeConfig]: ...

class DocTypeConfig(BaseModel):
    code: str
    prefix: str
    directory: str
    properties: List[PropertyConfig]
    lifecycle: Optional[dict]
    has_verification: bool = False
```

---

## DESIGN-012: GitOps Approval Model
*Implements REQ-001 (item creation)*

Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM) have no
`lifecycle` block in their doc-type config and no `status` field in their YAML files.

**Implementation:**
- `create_item()`: does not set `status` when `get_initial_state()` returns `None`
- `get_available_transitions()`: returns `[]` for items with no lifecycle config
- `is_item_editable()`: requirement items are always editable (no locked states)
- Git branch serves as the approval indicator; no field duplication needed

---

## DESIGN-013: Component Boundary Enforcement
*Implements REQ-010*

**Automated verification:** `DHF/utils/tests/test_srs_034_boundary.py`

The test uses Python `ast` module to scan all `.py` files in `src/compliantflow/`
and fail if any prohibited `utils.*` import is found outside the adapter boundary.

**Prohibited modules** (raises test failure if found in non-adapter `src/compliantflow/` code):
- `utils.repository`
- `utils.result_store`
- `utils.junit_parser`
- `utils.document_generation`

**LocalDHFAdapter location:** `DHF/utils/local_adapter.py`
(moved from `src/compliantflow/adapters/` in CR-019 to enforce the boundary fully).
