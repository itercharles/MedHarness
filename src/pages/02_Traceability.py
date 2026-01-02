"""Traceability Matrix - Focused visualization of requirements traceability."""
"""Traceability Matrix Page - Configurable traceability views."""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime
from traceability.compliant_flow_core import CompliantFlowCore
from traceability.models.item import VerificationStatus
from traceability.document_generator import DocumentGenerator
from streamlit_agraph import agraph, Node, Edge, Config
import networkx as nx
from test_results import VerificationStatusProvider
from utils.ui_helpers import check_and_show_item_detail, make_item_columns_clickable

# Page Configuration
st.set_page_config(
    page_title="Traceability - CompliantFlow",
    page_icon="🔗",
    layout="wide"
)

# Initialize Core
@st.cache_resource
def get_core():
    dhf_root = Path(__file__).resolve().parent.parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)

# Initialize Test Results Provider
@st.cache_resource
def get_test_provider():
    core = get_core()
    # Convert Pydantic model to dict
    config_dict = core.config.model_dump() if core.config else {}
    return VerificationStatusProvider(config_dict)

try:
    core = get_core()
    test_provider = get_test_provider()
except Exception as e:
    st.error(f"Failed to initialize: {e}")
    st.stop()

# Page Header
st.title("🔗 Traceability - CompliantFlow")
st.caption("Configurable traceability views")

# Check for item detail query parameter
if check_and_show_item_detail(core):
    st.markdown("---")

# Sidebar: View Mode Selection
st.sidebar.header("View Mode")
view_mode = st.sidebar.radio(
    "Select View",
    ["Matrix Table", "Vertical View", "Horizontal View"],
    help="Matrix Table: Complete traceability table\\nVertical: Focus on one document type\\nHorizontal: Trace one item's path"
)

# Helper Functions
def get_doc_type_code(item_id: str) -> str:
    """Get document type code from item ID."""
    for doc_type in core.config.doc_types:
        if item_id.startswith(doc_type.prefix):
            return doc_type.code
    return "OTHER"

def get_color_by_status(item: dict) -> str:
    """Get node color based on verification status."""
    status = item.get('verification_status')
    if status == VerificationStatus.PASS.value:
        return "#90EE90"  # Light green
    elif status == VerificationStatus.FAIL.value:
        return "#FFB6C1"  # Light pink
    else:
        return "#D3D3D3"  # Light gray

def get_shape_by_type(item_id: str) -> str:
    """Get node shape based on document type."""
    doc_type = get_doc_type_code(item_id)
    if doc_type.startswith('TC'):
        return "diamond"
    elif doc_type == 'CRS':
        return "ellipse"
    else:
        return "box"

def should_show_warning(item: dict, core) -> bool:
    """Check if item should show warning icon based on lifecycle state."""
    # Use core.is_item_editable() which checks global lifecycle
    return core.is_item_editable(item)

@st.cache_data(show_spinner="Building traceability matrix...")
def build_matrix_table(all_items: List[dict], path: List[str], _core) -> pd.DataFrame:
    """Build traceability table for a specific matrix configuration."""
    chains = []
    
    # Start with first level items
    start_type = path[0]
    start_items = [i for i in all_items if get_doc_type_code(i['id']) == start_type]
    
    for start_item in start_items:
        # Recursively build chains through the path
        _build_chains_recursive(all_items, path, 0, {path[0]: start_item}, chains, _core)
    
    # Add orphan rows for items at each level that aren't in any chain
    # Track which items are already in chains
    items_in_chains = {level: set() for level in path}
    for chain in chains:
        for level in path:
            if level in chain and chain[level] != '-':
                # Extract ID without warning icon
                item_id = chain[level].replace(' ⚠️', '')
                items_in_chains[level].add(item_id)
    
    # For each level, find orphan items and add them
    for level_idx, level in enumerate(path):
        level_items = [i for i in all_items if get_doc_type_code(i['id']) == level]
        
        for item in level_items:
            if item['id'] not in items_in_chains[level]:
                # This is an orphan item - create a row for it
                chain_row = {}
                
                # Add dashes for all previous levels
                for i in range(level_idx):
                    chain_row[path[i]] = '-'
                
                # Add this orphan item
                item_id = item['id']
                if should_show_warning(item, _core):
                    item_id = f"{item_id} ⚠️"
                chain_row[level] = item_id
                if level != path[-1]:
                    chain_row[f"{level} Title"] = item.get('title', 'N/A')[:50]
                
                # Add dashes for all following levels
                for i in range(level_idx + 1, len(path)):
                    chain_row[path[i]] = '-'
                
                # Mark as orphan
                chain_row['Status'] = f'⚠️ Orphan {level}'
                chains.append(chain_row)
    
    return pd.DataFrame(chains)

def _build_chains_recursive(all_items: List[dict], path: List[str], level: int, current_chain: dict, chains: List[dict], _core):
    """Recursively build traceability chains, creating multiple rows for multiple matches."""
    if level >= len(path) - 1:
        # Reached end of path, finalize chain
        chain_row = {}
        for doc_type, item in current_chain.items():
            # Add ID with warning icon if not in final state
            item_id = item['id']
            if should_show_warning(item, _core):
                item_id = f"{item_id} ⚠️"
            
            chain_row[doc_type] = item_id
            
            # Add title for non-last levels
            if doc_type != path[-1]:
                chain_row[f"{doc_type} Title"] = item.get('title', 'N/A')[:50]
        
        # Add verification status if this is the last level and it's a test case
        last_item = current_chain[path[-1]]
        if level == len(path) - 1 and last_item['id'].startswith(('TC-', 'tc-')):
            # Get dynamic verification status from provider
            try:
                status_info = test_provider.get_verification_status(last_item)
                verify_status = status_info.get('status', 'PENDING')
                
                # Add source indicator
                source = status_info.get('source', 'manual')
                if source == 'automated':
                    verify_status = f"🤖 {verify_status}"
                else:
                    verify_status = f"👤 {verify_status}"
                
                chain_row['Verify'] = verify_status
            except Exception as e:
                # Fallback to YAML field if provider fails
                chain_row['Verify'] = last_item.get('verification_status', 'PENDING')

        
        # Add status
        complete = len(current_chain) == len(path)
        chain_row['Status'] = '✅ Complete' if complete else '⚠️ Incomplete'
        chains.append(chain_row)
        return
    
    # Find next level items
    current_type = path[level]
    next_type = path[level + 1]
    current_item = current_chain[current_type]
    
    # Find all items of next_type that link to current_item
    # Works for all relationship types (derives_from, implements, design, etc.)
    # because all_linked_uids includes all typed relationships
    next_items = [item for item in all_items 
                 if get_doc_type_code(item['id']) == next_type 
                 and current_item['id'] in item.get('all_linked_uids', [])]
    
    if next_items:
        # Create a chain for each match (multiple rows)
        for next_item in next_items:
            new_chain = current_chain.copy()
            new_chain[next_type] = next_item
            _build_chains_recursive(all_items, path, level + 1, new_chain, chains, _core)
    else:
        # No match found, create incomplete chain
        chain_row = {}
        for doc_type, item in current_chain.items():
            # Add ID with warning icon if not in final state
            item_id = item['id']
            if should_show_warning(item, _core):
                item_id = f"{item_id} ⚠️"
            
            chain_row[doc_type] = item_id
            if doc_type != path[-1]:
                chain_row[f"{doc_type} Title"] = item.get('title', 'N/A')[:50]
        
        # Add missing levels as '-'
        for i in range(level + 1, len(path)):
            chain_row[path[i]] = '-'
        
        # Check if we should add verification column (based on path)
        if path[-1].startswith('TC-'):
            chain_row['Verify'] = '-'
        
        chain_row['Status'] = '⚠️ Incomplete'
        chains.append(chain_row)

def build_vertical_view(core, focus_type: str, show_upstream: bool, show_downstream: bool):
    """Build vertical view focusing on one document type."""
    nodes = []
    edges = []
    
    all_items = core.get_all_items()
    
    # Get focus items
    focus_items = [i for i in all_items if get_doc_type_code(i['id']) == focus_type]
    
    if not focus_items:
        return nodes, edges
    
    # Track all items to include
    items_to_show = {item['id']: item for item in focus_items}
    
    # Add upstream items (items that link TO focus items)
    if show_upstream:
        for item in all_items:
            for link in item.get('links', []):
                if link in items_to_show:
                    items_to_show[item['id']] = item
    
    # Add downstream items (items that focus items link TO)
    if show_downstream:
        for focus_item in focus_items:
            for link in focus_item.get('links', []):
                linked_item = next((i for i in all_items if i['id'] == link), None)
                if linked_item:
                    items_to_show[link] = linked_item
    
    # Build nodes
    for item_id, item in items_to_show.items():
        is_focus = get_doc_type_code(item_id) == focus_type
        
        nodes.append(Node(
            id=item['id'],
            label=item['id'],
            title=item.get('title', item['id']),
            color=get_color_by_status(item),
            shape=get_shape_by_type(item['id']),
            size=35 if is_focus else 25,
            borderWidth=3 if is_focus else 1,
            borderWidthSelected=5 if is_focus else 3
        ))
    
    # Build edges
    item_ids = set(items_to_show.keys())
    for item in items_to_show.values():
        for link in item.get('links', []):
            if link in item_ids:
                edges.append(Edge(
                    source=item['id'],
                    target=link,
                    color='#999999'
                ))
    
    return nodes, edges

def build_horizontal_view(core, start_item_id: str):
    """Build horizontal view tracing one item's path."""
    nodes = []
    edges = []
    
    all_items = core.get_all_items()
    
    # Build NetworkX graph for path finding
    G = nx.DiGraph()
    item_map = {item['id']: item for item in all_items}
    
    for item in all_items:
        G.add_node(item['id'])
        for link in item.get('links', []):
            G.add_edge(item['id'], link)
    
    if start_item_id not in G:
        return nodes, edges
    
    # Find all reachable nodes (downstream)
    downstream = nx.descendants(G, start_item_id)
    downstream.add(start_item_id)
    
    # Find all nodes that can reach start (upstream)
    upstream = nx.ancestors(G, start_item_id)
    
    # Combine all nodes in trace path
    trace_nodes = downstream | upstream
    
    # Build nodes
    for node_id in trace_nodes:
        if node_id not in item_map:
            continue
        
        item = item_map[node_id]
        is_start = node_id == start_item_id
        
        nodes.append(Node(
            id=item['id'],
            label=item['id'],
            title=item.get('title', item['id']),
            color="#FFD700" if is_start else get_color_by_status(item),  # Gold for start
            shape=get_shape_by_type(item['id']),
            size=40 if is_start else 25,
            borderWidth=4 if is_start else 1
        ))
    
    # Build edges
    for node_id in trace_nodes:
        if node_id not in item_map:
            continue
        
        item = item_map[node_id]
        for link in item.get('links', []):
            if link in trace_nodes:
                edges.append(Edge(
                    source=item['id'],
                    target=link,
                    color='#999999'
                ))
    
    return nodes, edges

# Main Content based on view mode
if view_mode == "Matrix Table":
    st.subheader("📊 Traceability Matrices")
    st.caption("Configurable traceability matrices showing different trace paths")
    
    # Get matrix configurations
    matrices = core.config.traceability_matrices
    
    if not matrices:
        st.warning("No traceability matrices configured in project_config.yaml")
        st.info("Add 'traceability_matrices' section to your configuration to define custom trace paths.")
    else:
        # Matrix selector
        matrix_names = [m.name for m in matrices]
        selected_matrix_name = st.selectbox(
            "Select Matrix",
            options=matrix_names,
            help="Choose which traceability matrix to display"
        )
        
        # Get selected config
        matrix_config = next(m for m in matrices if m.name == selected_matrix_name)
        
        # Display description and path
        st.write(f"**Description**: {matrix_config.description}")
        st.write(f"**Trace Path**: {' → '.join(matrix_config.path)}")
        
        # Build table
        all_items = core.get_all_items()
        df = build_matrix_table(all_items, matrix_config.path, core)
        
        if df.empty:
            st.warning(f"No items found for trace path: {' → '.join(matrix_config.path)}")
        else:
            # Show statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Chains", len(df))
            with col2:
                complete = len(df[df['Status'] == '✅ Complete'])
                st.metric("Complete", complete)
            with col3:
                incomplete = len(df[df['Status'] != '✅ Complete'])
                st.metric("Incomplete", incomplete)
            with col4:
                coverage = (complete / len(df) * 100) if len(df) > 0 else 0
                st.metric("Coverage", f"{coverage:.0f}%")
            
            # Build column config with clickable item IDs
            df, column_config = make_item_columns_clickable(df, core)
            
            # Add custom config for other columns
            for col in df.columns:
                if col not in column_config:
                    if col == 'Status':
                        column_config[col] = st.column_config.TextColumn("Status", width="small")
                    elif 'Title' in col:
                        column_config[col] = st.column_config.TextColumn(col, width="medium")
                    else:
                        column_config[col] = st.column_config.TextColumn(col, width="small")
            
            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                height=600,
                column_config=column_config
            )

elif view_mode == "Vertical View":
    st.subheader("📊 Vertical View - Document Type Focus")
    st.caption("Focus on one document type and its immediate relationships")
    
    # Sidebar controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("Vertical View Settings")
    
    all_doc_types = [dt.code for dt in core.config.doc_types]
    focus_type = st.sidebar.selectbox(
        "Focus Document Type",
        options=all_doc_types,
        index=all_doc_types.index("SYS") if "SYS" in all_doc_types else 0
    )
    
    show_upstream = st.sidebar.checkbox("Show Upstream Links", value=True, help="Show items that link TO this type")
    show_downstream = st.sidebar.checkbox("Show Downstream Links", value=True, help="Show items this type links TO")
    
    # Build graph
    nodes, edges = build_vertical_view(core, focus_type, show_upstream, show_downstream)
    
    if not nodes:
        st.warning(f"No items found for document type: {focus_type}")
    else:
        # Show statistics
        col1, col2, col3 = st.columns(3)
        focus_count = len([n for n in nodes if get_doc_type_code(n.id) == focus_type])
        with col1:
            st.metric("Focus Items", focus_count)
        with col2:
            st.metric("Total Nodes", len(nodes))
        with col3:
            st.metric("Total Links", len(edges))
        
        # Graph
        config = Config(
            width=1200,
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6"
        )
        
        selected = agraph(nodes, edges, config)
        
        # Show selected item details
        if selected:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📄 Selected Item")
            try:
                item = core.get_item(selected)
                st.sidebar.write(f"**ID**: {item['id']}")
                st.sidebar.write(f"**Title**: {item.get('title', 'N/A')}")
                st.sidebar.write(f"**Type**: {get_doc_type_code(item['id'])}")
                st.sidebar.write(f"**Status**: {item.get('status', 'N/A')}")
                st.sidebar.write(f"**Verification**: {item.get('verification_status', 'N/A')}")
                
                if item.get('links'):
                    st.sidebar.write(f"**Links ({len(item['links'])})**:")
                    for link in item['links']:
                        st.sidebar.write(f"  • {link}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

else:  # Horizontal View
    st.subheader("🔍 Horizontal View - Item Trace Path")
    st.caption("Trace the complete path of a single item from source to end")
    
    # Sidebar controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("Horizontal View Settings")
    
    all_items = core.get_all_items()
    item_ids = [item['id'] for item in all_items]
    item_ids.sort()
    
    start_item = st.sidebar.selectbox(
        "Select Item to Trace",
        options=item_ids,
        help="Select an item to see its complete traceability path"
    )
    
    # Build graph
    nodes, edges = build_horizontal_view(core, start_item)
    
    if not nodes:
        st.warning(f"No trace path found for item: {start_item}")
    else:
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Traced Item", start_item)
        with col2:
            st.metric("Connected Items", len(nodes) - 1)
        with col3:
            st.metric("Total Links", len(edges))
        
        # Show item details
        try:
            start_item_data = core.get_item(start_item)
            with st.expander("📄 Traced Item Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title**: {start_item_data.get('title', 'N/A')}")
                    st.write(f"**Type**: {get_doc_type_code(start_item)}")
                    st.write(f"**Status**: {start_item_data.get('status', 'N/A')}")
                with col2:
                    st.write(f"**Verification**: {start_item_data.get('verification_status', 'N/A')}")
                    if start_item_data.get('links'):
                        st.write(f"**Direct Links**: {', '.join(start_item_data['links'])}")
        except Exception as e:
            st.error(f"Error loading item: {e}")
        
        # Graph
        config = Config(
            width=1200,
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6"
        )
        
        selected = agraph(nodes, edges, config)
        
        # Show selected item details
        if selected and selected != start_item:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📄 Selected Item")
            try:
                item = core.get_item(selected)
                st.sidebar.write(f"**ID**: {item['id']}")
                st.sidebar.write(f"**Title**: {item.get('title', 'N/A')}")
                st.sidebar.write(f"**Type**: {get_doc_type_code(item['id'])}")
                st.sidebar.write(f"**Status**: {item.get('status', 'N/A')}")
                st.sidebar.write(f"**Verification**: {item.get('verification_status', 'N/A')}")
                
                if item.get('links'):
                    st.sidebar.write(f"**Links ({len(item['links'])})**:")
                    for link in item['links']:
                        st.sidebar.write(f"  • {link}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

# Export Section
st.markdown("---")
st.subheader("📥 Export")

col_exp1, col_exp2 = st.columns([3, 1])
with col_exp1:
    st.write("Generate a comprehensive PDF traceability matrix report including coverage analysis and orphan detection.")
with col_exp2:
    if st.button("📄 Generate PDF Report", type="primary"):
        with st.spinner("Generating traceability matrix PDF..."):
            try:
                # Initialize document generator - use DHF templates
                template_dir = Path(__file__).resolve().parent.parent.parent / "DHF" / "documents" / "specifications" / "templates"
                doc_gen = DocumentGenerator(core, template_dir)
                
                # Generate PDF
                pdf_path = doc_gen.generate_traceability_matrix()
                
                # Read PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Offer download
                st.download_button(
                    label="⬇️ Download Traceability Matrix PDF",
                    data=pdf_data,
                    file_name=f"Traceability_Matrix_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
                st.success("✅ PDF generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating PDF: {e}")
                st.exception(e)

# Legend
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Colors:**")
    st.markdown("🟢 Green = PASS")
    st.markdown("🔴 Pink = FAIL")
    st.markdown("⚪ Gray = PENDING")
    if view_mode == "Horizontal View":
        st.markdown("🟡 Gold = Traced Item")

with col2:
    st.markdown("**Shapes:**")
    st.markdown("◆ Diamond = Test Cases")
    st.markdown("⬭ Ellipse = Customer Requirements")
    st.markdown("▢ Box = Other Requirements")
