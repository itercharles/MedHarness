# Architecture Design Specification

## 1. Introduction
CompliantFlow is a lightweight, Docs-as-Code Application Lifecycle Management (ALM) tool designed for medical device software development.

## 2. System View

### 2.1 Data Layer
- **Storage**: Structured data (Requirements, Tests, Risks) is stored as YAML files. Unstructured data (Plans, Manuals) is stored as Markdown.
- **Version Control**: Git is used as the single source of truth for all data, providing history, branching, and audit trails.
- **Models**:
    - `Item`: A Pydantic v2 model representing any traceable artifact. Supports dynamic fields via configuration.
    - `ProjectConfig`: A Pydantic model for validating `project_config.yaml`.

### 2.2 Logic Layer
- **Core Facade**: `CompliantFlowCore` initializes the system, loading configuration and data.
- **Graph Engine**: `GraphEngine` wraps `networkx.DiGraph`. It handles:
    - Building the graph from `Item` objects.
    - Resolving internal links.
    - Calculating metrics (coverage, orphan counts).
    - Traversing upstream/downstream dependencies.
- **Persistence**: `ItemLoader` and `ItemSaver` abstract filesystem operations.

### 2.3 Presentation Layer
- **Streamlit App**: The primary user interface for debugging and visualization.
    - **Sidebar**: Provides filtering and configuration view.
    - **Data View**: Uses `st.dataframe` to display tabular data.
    - **Graph Visualization**: Uses `streamlit-agraph` to render interactive force-directed graphs.

## 3. Data Flow
1.  **Load**: `ItemLoader` scans the repository, parsing YAML files into Pydantic `Item` objects.
2.  **Build**: `GraphEngine` accepts the list of Items, adding them as nodes and creating edges for valid links.
3.  **Query**: The UI requests data from `CompliantFlowCore`.
4.  **Render**: Streamlit displays the processed data to the user.
