import streamlit as st
import pandas as pd
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
from streamlit_agraph import agraph, Node, Edge, Config
import networkx as nx

st.set_page_config(layout="wide", page_title="CompliantFlow Debugger")

# Initialize Core
@st.cache_resource
def get_core():
    # Assuming this file is in backend/
    # Data is in ../repo_root
    repo_root = Path(__file__).resolve().parent.parent / "repo_root"
    return CompliantFlowCore(repo_root)

try:
    core = get_core()
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# Sidebar
st.sidebar.title("CompliantFlow")
st.sidebar.header("Filters")

# Get all items
items = core.get_all_items()
st.sidebar.info(f"Loaded {len(items)} items from {core.repo_root}")

if not items:
    st.warning("No items found! Check your repository path and specifications folder.")
    df = pd.DataFrame(columns=["id", "title", "content", "verification_status", "links"])
else:
    df = pd.DataFrame(items)
    # Ensure columns exist even if data is partial
    expected_cols = ["id", "title", "content", "verification_status", "links"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

# Filter by Type
if core.config:
    doc_types = [dt.code for dt in core.config.doc_types]
    selected_types = st.sidebar.multiselect("Document Types", doc_types, default=doc_types)
else:
    selected_types = []
    st.sidebar.warning("No config loaded")

# Filter by Status
statuses = ["PASS", "FAIL", "PENDING"] # Add more if needed
selected_statuses = st.sidebar.multiselect("Verification Status", statuses, default=statuses)

# Apply Filters
if not df.empty:
    # Filter by Type (prefix)
    if selected_types:
        # Create a regex pattern to match any of the selected prefixes
        # Assuming ID starts with prefix
        # Actually, let's just check if ID starts with any of the selected type prefixes
        # We need to map code to prefix first
        type_prefixes = [core.config.get_doc_type(t).prefix for t in selected_types if core.config.get_doc_type(t)]
    # Filter by Type (prefix)
    if selected_types:
        # Create a regex pattern to match any of the selected prefixes
        # Assuming ID starts with prefix
        # Actually, let's just check if ID starts with any of the selected type prefixes
        # We need to map code to prefix first
        type_prefixes = [core.config.get_doc_type(t).prefix for t in selected_types if core.config.get_doc_type(t)]
        mask_type = df['id'].apply(lambda x: any(x.startswith(p) for p in type_prefixes))
        df = df[mask_type]

    # Filter by Status
    if selected_statuses:
        # Handle None/NaN statuses
        df['verification_status'] = df['verification_status'].fillna('PENDING')
        df = df[df['verification_status'].isin(selected_statuses)]

# Main Content
st.title("Traceability Debugger")

tab1, tab2, tab3, tab4 = st.tabs(["Data View", "Orphan Analysis", "Graph Visualization", "Compliance"])

with tab1:
    st.header(f"Items ({len(df)})")
    
    if not selected_types:
        st.info("Select Document Types in sidebar to view items.")
    
    for doc_code in selected_types:
        # Get config for this type
        doc_type = core.config.get_doc_type(doc_code)
        if not doc_type:
            continue
            
        # Filter df for this type
        # Assuming ID starts with prefix.
        prefix = doc_type.prefix
        subset = df[df['id'].str.startswith(prefix, na=False)]
        
        if subset.empty:
            continue
            
        # Determine columns to display based on config
        display_cols = ["id"] # Always include ID
        if doc_type.properties:
            # Add configured properties if they exist in the dataframe
            for prop in doc_type.properties:
                if prop != "id" and prop in subset.columns:
                    display_cols.append(prop)
        else:
            # Fallback if no properties defined
            target_cols = ["title", "content", "verification_status", "links", "hazard", "cause", "effect"]
            for col in target_cols:
                if col in subset.columns:
                     display_cols.append(col)

        # Dynamic Column Config
        col_config = {
            "id": "ID",
            "title": "Title",
            "links": "Links"
        }
        
        if "verification_status" in display_cols:
             col_config["verification_status"] = st.column_config.TextColumn(
                "Status",
                help="Verification Status",
                validate="^(PASS|FAIL|PENDING)$"
            )
            
        with st.expander(f"{doc_type.name} ({len(subset)})", expanded=True):
            st.dataframe(
                subset[display_cols], 
                width='stretch',
                column_config=col_config
            )

with tab2:
    st.subheader("Orphan Analysis")
    
    # Find orphans using core graph engine
    orphans = core.graph.find_orphans()
    
    if orphans:
        st.warning(f"Found {len(orphans)} orphan items.")
        orphan_df = pd.DataFrame(orphans)
        st.dataframe(orphan_df, width='stretch')
    else:
        st.success("No orphan items found! All items are connected.")

    # Stub Existence Check (Manual implementation for now as rule was removed)
    st.subheader("Stub Existence Check")
    # Simple check: items with 'TBD' in content
    if not df.empty and 'content' in df.columns:
        stubs = df[df['content'].str.contains('TBD', case=False, na=False)]
        if not stubs.empty:
            st.warning(f"Found {len(stubs)} potential stubs (containing 'TBD').")
            st.dataframe(stubs[['id', 'title', 'content']], width='stretch')
        else:
            st.success("No 'TBD' stubs found.")

with tab3:
    st.subheader("Traceability Graph")
    
    # Graph Settings
    st.sidebar.header("Graph Settings")
    show_physics = st.sidebar.checkbox("Enable Physics", value=True)
    directed = st.sidebar.checkbox("Directed", value=True)
    
    # Build Graph for Visualization
    # We use the filtered dataframe to limit nodes, but we need to include their connections
    
    if len(df) > 100:
        st.warning("Too many items to visualize efficiently. Showing top 100.")
        viz_ids = set(df.head(100)['id'])
    else:
        viz_ids = set(df['id'])
        
    nodes = []
    edges = []
    
    # Add Nodes from Graph (ensures we see exactly what's in the engine)
    # We only show nodes that are in our filtered list
    for node_id, data in core.graph.graph.nodes(data=True):
        if node_id not in viz_ids:
            continue
            
        item = data.get('item')
        if not item:
            continue
            
        # Color based on status
        color = "#90EE90" # Light Green
        status = getattr(item, 'verification_status', None)
        if status == 'FAIL':
            color = "#FFB6C1" # Light Pink
        elif status == 'PENDING' or status is None:
            color = "#D3D3D3" # Light Grey
            
        # Shape based on type (heuristic)
        shape = "box"
        if node_id.startswith('USN'): shape = "ellipse"
        elif node_id.startswith('TC'): shape = "diamond"
            
        nodes.append(Node(
            id=node_id,
            label=node_id,
            title=item.title or "",
            color=color,
            shape=shape
        ))
        
    # Add Edges from Graph
    for u, v, data in core.graph.graph.edges(data=True):
        if u in viz_ids and v in viz_ids:
            edges.append(Edge(
                source=u,
                target=v,
                label=data.get('type', 'traces'),
                color="#888888"
            ))
            
    config = Config(
        width=1000,
        height=600,
        directed=directed, 
        physics=show_physics, 
        hierarchical=False,
    )

    return_value = agraph(nodes=nodes, edges=edges, config=config)

with tab4:
    st.subheader("Compliance Report")
    
    # Load available policy groups (mocked or scanned)
    # For now, hardcode IEC_62304 or scan directory
    governance_dir = core.repo_root / "governance"
    if governance_dir.exists():
        groups = [f.stem for f in governance_dir.glob("*.yaml")]
    else:
        groups = []
        
    if not groups:
        st.info("No policy groups found in repo_root/governance")
    else:
        selected_group = st.selectbox("Select Policy Group", groups)
        
        # Display Group Details
        group_data = core.get_policy_group(selected_group)
        if group_data:
            st.write(f"**{group_data.get('title', selected_group)}** (Version: {group_data.get('version', 'N/A')})")
            
            policies = group_data.get('policies', [])
            if policies:
                st.subheader("Defined Policies")
                p_df = pd.DataFrame(policies)
                # Select columns: id, text (rename to Content), status
                cols = ['id', 'text', 'status']
                p_df = p_df[cols]
                
                st.dataframe(
                    p_df,
                    width='stretch',
                    column_config={
                        "id": "ID",
                        "text": "Content",
                        "status": st.column_config.TextColumn(
                            "Status",
                            validate="^(approved|draft|rejected)$"
                        )
                    }
                )
            else:
                st.info("No policies defined in this document.")
        
        if st.button("Check Compliance"):
            with st.spinner(f"Checking {selected_group}..."):
                report = core.check_compliance(selected_group)
                
            if report:
                score = report['score']
                st.progress(score / 100, text=f"Compliance Score: {score:.1f}%")
                
                # Display Results
                res_df = pd.DataFrame(report['results'])
                
                # Status Icon
                def get_status_icon(passed):
                    return "✅" if passed else "❌"
                
                res_df['Status'] = res_df['passed'].apply(get_status_icon)
                
                # Merge with policy definitions to get Text/Content
                # We need p_df (defined above)
                if 'p_df' in locals() and not p_df.empty:
                    # Rename id to policy_id for merge or vice versa
                    p_df_merge = p_df.rename(columns={'id': 'policy_id', 'text': 'content'})
                    merged_df = pd.merge(res_df, p_df_merge, on='policy_id', how='left')
                    
                    # Display merged table
                    st.dataframe(
                        merged_df[['Status', 'policy_id', 'content', 'details']],
                        width='stretch',
                        column_config={
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "policy_id": "Policy ID",
                            "content": "Content",
                            "details": "Details"
                        }
                    )
                else:
                    st.dataframe(
                        res_df[['Status', 'policy_id', 'details']],
                        width='stretch',
                        column_config={
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "policy_id": "Policy ID",
                            "details": "Details"
                        }
                    )
                
                # Expandable Evidence
                st.subheader("Detailed Evidence")
                for res in report['results']:
                    with st.expander(f"{get_status_icon(res['passed'])} {res['policy_id']}"):
                        st.write(f"**Passed**: {res['passed']}")
                        st.write(f"**Details**: {res['details']}")
                        if res.get('evidence'):
                            st.json(res['evidence'])
            else:
                st.error("Failed to generate report.")
