"""Traceability Matrix - Focused visualization of requirements traceability."""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from pathlib import Path
from typing import Dict, List, Set, Tuple
from traceability.compliant_flow_core import CompliantFlowCore
from traceability.models.item import VerificationStatus
import networkx as nx

st.set_page_config(
    page_title="Traceability Matrix",
    page_icon="🔗",
    layout="wide"
)

# Initialize
@st.cache_resource
def get_core():
    dhf_root = Path(__file__).resolve().parent.parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)

core = get_core()

# Page Header
st.title("🔗 Traceability Matrix")
st.caption("Focused visualization of requirements traceability")

# Sidebar: View Mode Selection
st.sidebar.header("View Mode")
view_mode = st.sidebar.radio(
    "Select View",
    ["Vertical View", "Horizontal View"],
    help="Vertical: Focus on one document type\nHorizontal: Trace one item's path"
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
if view_mode == "Vertical View":
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
