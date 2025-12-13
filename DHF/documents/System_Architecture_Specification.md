# Architecture Design Specification

## 1. Introduction
CompliantFlow is a lightweight, Docs-as-Code Application Lifecycle Management (ALM) tool designed for medical device software development.

## 2. System View

### 2.1 Data Layer
- **Storage**: Structured data (Requirements, Tests, Risks) is stored as YAML files. Unstructured data (Plans, Manuals) is stored as Markdown.
- **Governance**: Regulations and Procedures are stored as structured YAML policies in `DHF/governance`.
- **Version Control**: Git is used as the single source of truth for all data, providing history, branching, and audit trails.
- **Models**:
    - `Item`: A Pydantic v2 model representing any traceable artifact. Supports dynamic fields via configuration.
    - `Regulation`/`Policy`: Models for compliance data.
    - `ProjectConfig`: A Pydantic model for validating `project_config.yaml`.

### 2.2 Logic Layer
- **Core Facade**: `CompliantFlowCore` initializes the system, loading configuration and data.
- **Graph Engine**: `GraphEngine` wraps `networkx.DiGraph`. It handles:
    - Building the graph from `Item` objects.
    - Resolving internal links.
    - Calculating metrics (coverage, orphan counts).
    - Traversing upstream/downstream dependencies.
- **Policy Engine**: `PolicyEngine` executes automated checks (e.g., `trace_coverage`, `item_existence`) against the graph.
- **Persistence**: `ItemLoader` and `ItemSaver` abstract filesystem operations.

### 2.3 Presentation Layer
- **Streamlit App**: The primary user interface for debugging and visualization.
    - **Sidebar**: Provides filtering and configuration view.
    - **Data View**: dynamically renders tables based on item types and configured properties.
    - **Graph Visualization**: Uses `streamlit-agraph` to render interactive force-directed graphs.
    - **Compliance Tab**: Allows executing regulatory checks and viewing detailed pass/fail reports.

## 3. Data Flow
1.  **Load**: `ItemLoader` scans the repository, parsing YAML files into Pydantic `Item` objects.
2.  **Build**: `GraphEngine` accepts the list of Items, adding them as nodes and creating edges for valid links.
3.  **Query**: The UI requests data from `CompliantFlowCore`.
4.  **Render**: Streamlit displays the processed data to the user.

## 3. Traceability to Requirements
The following table demonstrates the traceability of Software Architecture Design (SDS) items to System Requirements (SYS).

| ID | Title | Trace to Requirements (SYS) |
|---|---|---|
| [SDS-001](file:///DHF/items/04_req_sds/SDS-001.yaml) | Graph Data Structure | [SYS-002](file:///DHF/items/02_req_sys/SYS-002.yaml) |
| [SDS-002](file:///DHF/items/04_req_sds/SDS-002.yaml) | Streamlit Visualization | [SYS-003](file:///DHF/items/02_req_sys/SYS-003.yaml) |
| [SDS-003](file:///DHF/items/04_req_sds/SDS-003.yaml) | Policy Engine | [SYS-006](file:///DHF/items/02_req_sys/SYS-006.yaml) |
