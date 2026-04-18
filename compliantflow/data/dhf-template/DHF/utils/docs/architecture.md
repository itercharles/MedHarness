# DHF Utils — Architecture

Architectural decisions for the `DHF/utils/` data-layer package.

---

## ARCH-001: Item Management Module

**Responsibilities:**
- Load items from YAML files with schema validation
- Save items with Git commit tracking
- Support configurable item types from project configuration
- Maintain item history and audit trail

**Key Interfaces:**
- `ItemLoader` (`repository/loader.py`) — load items from file system by ID, type, or all items
- `ItemSaver` (`repository/saver.py`) — save items with validation and Git commits
- Schema validation per doc type using `ProjectConfig`

**Implementation Notes:**
- YAML format for human-readable storage
- Git integration provides automatic version control
- Pydantic models for type-safe item validation
- File-based storage enables simple backup and portability

---

## ARCH-002: Traceability Analysis Module

**Responsibilities:**
- Build directed graph from item links
- Find upstream/downstream dependencies
- Detect orphan items
- Calculate coverage metrics

**Key Interfaces:**
- `GraphEngine` (`src/compliantflow/traceability/graph/engine.py`) — builds NetworkX DiGraph
- Edge direction: **child → parent** (e.g. `SRS-001 → SYS-001` for `derives_from`)
- `nx.descendants(G, id)` = business **upstream** (parents)
- `nx.ancestors(G, id)` = business **downstream** (children)

**Implementation Notes:**
- Uses NetworkX for graph operations
- In-memory graph rebuilt on `refresh()`
- Configurable relationship types via doc type config

---

## ARCH-003: Lifecycle Management Module

**Scope:** Explicit lifecycle applies **only to CR, REL, and DEF**.
Requirement items (UC, CRS, SYS, SRS, SWDD, SYSARCH, SOUP, RISK, RCM) use the
GitOps approval model — no `status` field, no transitions.

**Responsibilities:**
- Load lifecycle configuration from doc-type config
- Validate state transitions for CR/REL/DEF
- Execute transition criteria (field validation, manual approval)
- Expose `get_available_transitions()` returning `[]` for requirement items

**Key Interfaces:**
- `get_initial_state()` → `None` for requirement types
- `get_available_transitions(item)` → `[]` for items with no lifecycle config
- `execute_transition(item_id, to_state, performed_by)` — validates criteria then writes status

---

## ARCH-004: Compliance Validation Module

**Responsibilities:**
- Load policy definitions from `DHF/governance/` YAML files
- Execute validation rules against DHF items
- Calculate compliance scores per policy group
- Collect pass/fail evidence

**Key Interfaces:**
- `PolicyEngine` (`src/compliantflow/traceability/compliance/`) — load and execute rules
- Policy YAML format: groups of named rules with type, parameters, and pass condition
- Supported rule types: coverage, orphan detection, status checks, field presence

---

## ARCH-005: Document Generation Module

**Responsibilities:**
- Render Jinja2 templates with item data → Markdown
- Export Markdown to PDF via WeasyPrint
- Track document versions automatically

**Key Interfaces:**
- `DocumentGenerator` (`document_generation.py`) — orchestrates template rendering
- Templates stored in `DHF/documents/specifications/templates/`
- Output written to `DHF/documents/specifications/`

**Implementation Notes:**
- Jinja2 for flexible templating
- WeasyPrint for professional PDF generation
- Version extracted from existing document header; incremented on each run

---

## ARCH-006: Test Integration Module

**Framework-agnostic boundary:**
- `DHF/utils/` consumes only JUnit XML — no coupling to any specific test framework
- `tests/` contains the pytest-specific adapter (`conftest.py` + `docstring_parser.py`)
- Any framework producing JUnit XML with `compliantflow.*` properties is compatible

**Responsibilities:**
- Parse JUnit XML produced by any test framework
- Extract TC IDs from `compliantflow.id` property or test name regex
- Persist results to `DHF/test-results/results.yaml` (git-ignored local cache)
- Recompute `verification_status` on linked requirement items after import

**Key Interfaces:**
- `parse_junit_xml(path)` → `List[ExecutionResult]` (`junit_parser.py`)
- `ResultStore.record_execution(...)` — upsert one TC record (`result_store.py`)
- `GitHubArtifactFetcher.fetch(run_id, commit_sha)` — on-demand CI artifact retrieval (`artifact_fetcher.py`)

**On-demand retrieval (CR-019):**
- CI runs tests → uploads JUnit XML as GitHub Actions artifact → done
- DHF fetches from artifacts via `compliantflow test pull` (or transparently on first access when `GITHUB_TOKEN` is set)
- `results.yaml` is a local cache only (`git rm`'d from repo, git-ignored)

---

## ARCH-007: GitOps-Based Approval Architecture

**Decision:** Requirement items use Git as the sole approval mechanism.

| Branch | Meaning |
|--------|---------|
| `main` | Item is **approved** (PR merge = approval evidence) |
| Feature branch | Item is **draft / under review** |
| Deleted from repo | Item is **retired** |

**Only CR, REL, and DEF retain explicit lifecycle** because they have multi-step
processes (e.g. CR: `draft → in_review → approved → implementing → completed`)
beyond the binary approved/not-approved that Git provides.

**Rationale:**
- Eliminates redundant `status: approved` fields on requirement YAML files
- Prevents stale approval metadata when items are edited on branches
- Git PR review (with required reviewers and CI checks) already serves as the approval gate
- Simplifies the data model: requirement items are pure content files, not workflow objects

**Implementation:**
- `project_config.yaml`: no `lifecycle` block on requirement doc types
- `create_item()`: does not set `status` when `get_initial_state()` returns `None`
- `get_available_transitions()`: returns `[]` for items with no lifecycle config

---

## ARCH-008: Three-Component Architecture Boundary Model

The system has three components with explicit import rules enforced by CI.

```
┌───────────────────────────────────┐
│  DHF/utils/          [data layer] │
│  YAML I/O, config, results, docs  │
│  Public API: utils/__init__.py    │
└──────────────┬────────────────────┘
               │  DHFAdapter protocol
               │  (adapters/protocol.py)
┌──────────────▼────────────────────┐
│  src/compliantflow/  [analysis]   │
│  Traceability, compliance, CLI    │
│  MAY import: utils.models.*,      │
│              utils.exceptions     │
│  MUST NOT:   utils.repository.*,  │
│              utils.result_store,  │
│              utils.junit_parser,  │
│              utils.document_gen.  │
└───────────────────────────────────┘
               │
┌──────────────▼────────────────────┐
│  tests/sys/, tests/crs/           │
│  Use ONLY CompliantFlowCore API   │
│                                   │
│  DHF/utils/tests/                 │
│  MAY import utils.* directly      │
│  MUST NOT access _adapter privates│
└───────────────────────────────────┘
```

**Adapter pattern:**
`DHFAdapter` (Protocol in `adapters/protocol.py`) is the sole interface between
the compliantflow analysis layer and DHF I/O for all data operations.
`LocalDHFAdapter` (`DHF/utils/local_adapter.py`) is the concrete implementation.

**Why shared models cross the boundary:**
`Item` and `ProjectConfig` are pure data DTOs with no I/O side effects.
Importing them directly is equivalent to sharing a schema definition.

**Enforcement:**
Verified by `test_sys_034_boundary.py` (AST import scan) which runs in CI on every PR.
