"""
CompliantFlow - Medical Device Design History File Management System
Main Streamlit application entry point.
"""

# Load environment variables from .env file FIRST (if available)
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass  # dotenv not installed, skip loading .env file


print("[APP] Loading app.py module...")

import streamlit as st
import yaml
from compliantflow.core import CompliantFlowCore
from debug_view.page_generator import generate_doc_type_pages

print("[APP] Imports completed successfully")
import pandas as pd
from helpers.ui_helpers import check_and_show_item_detail


def get_dhf_root() -> Path:
    """
    Get DHF root directory from configuration.
    
    Returns:
        Path to DHF directory
    """
    # Check for environment variable override (used by tests)
    import os
    env_dhf = os.environ.get("COMPLIANTFLOW_DHF_ROOT")
    if env_dhf:
        print(f"[APP] Using DHF from environment: {env_dhf}")
        return Path(env_dhf)

    # Default to production DHF
    return Path(__file__).resolve().parent.parent / "DHF"


# Initialize Core
@st.cache_resource
def get_core():
    """
    Initialize CompliantFlowCore.
    
    Note: DHF root is resolved dynamically.
    """
    dhf_root = get_dhf_root()
    return CompliantFlowCore(dhf_root)


def home_page():
    # Main page content
    st.title("📋 CompliantFlow")
    st.markdown("""
    Welcome to **CompliantFlow** - your Medical Device Design History File (DHF) management system.

    ### Quick Navigation
    Use the sidebar to navigate between different sections:
    - **📊 Dashboard**: Overview of your DHF status and metrics
    - **📝 Items**: Browse and manage traceability items
    - **🔗 Traceability**: View relationships and traceability matrices
    - **✅ Compliance**: Compliance assessment and reporting

    ### Getting Started
    1. Browse existing items in the sidebar
    2. Create new items using the "New" button
    3. Link items to establish traceability
    4. Generate compliance reports

    ---
    """)

    # Show recent activity
    st.subheader("📈 Recent Activity")

    # Get all items
    all_items = st.session_state.core.get_all_items()

    if all_items:
        # Convert to DataFrame for display
        df = pd.DataFrame(all_items)
        
        # Show summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(all_items))
        
        with col2:
            # Count by status
            if 'status' in df.columns:
                approved_count = len(df[df['status'] == 'approved'])
                st.metric("Approved Items", approved_count)
            else:
                st.metric("Approved Items", "N/A")
        
        with col3:
            # Count unique document types
            if 'id' in df.columns:
                doc_types = df['id'].str.extract(r'^([A-Z]+)-')[0].nunique()
                st.metric("Document Types", doc_types)
            else:
                st.metric("Document Types", "N/A")
        
        with col4:
            # Count items with links
            if 'all_linked_uids' in df.columns:
                linked_count = len(df[df['all_linked_uids'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)])
                st.metric("Linked Items", linked_count)
            else:
                st.metric("Linked Items", "N/A")
        
        # Show recent items
        st.subheader("Recent Items")
        recent_df = df.head(10)[['id', 'title', 'status']].copy() if 'title' in df.columns and 'status' in df.columns else df.head(10)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info("No items found in DHF. Create your first item to get started!")


# === PAGE CONFIGURATION ===
st.set_page_config(
    page_title="CompliantFlow",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CORE INITIALIZATION ===
try:
    # Get config file path (use default location)
    st.session_state.core = get_core()
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# === GENERATE PAGES ===
# Generate dynamic pages for each document type
try:
    doc_type_pages = generate_doc_type_pages(st.session_state.core)
    print(f"[APP] Generated {len(doc_type_pages)} dynamic pages")
    if not doc_type_pages:
        st.warning("No document type pages were generated. Check your configuration.")
except Exception as e:
    st.error(f"Failed to generate document type pages: {e}")
    print(f"[ERROR] Page generation failed: {e}")
    import traceback
    traceback.print_exc()
    doc_type_pages = []

# Convert to st.Page objects with url_path
all_pages = []
for page_number, name, icon, page_func, code in doc_type_pages:
    all_pages.append(st.Page(page_func, title=name, icon=icon, url_path=f"page_{code}"))

# Add static pages with absolute paths
src_dir = Path(__file__).parent
traceability_path = (src_dir / "debug_view" / "02_Traceability.py").resolve()
compliance_path = (src_dir / "debug_view" / "03_Compliance.py").resolve()

if traceability_path.exists():
    all_pages.append(st.Page(str(traceability_path), title="Traceability", icon="🔗"))
if compliance_path.exists():
    all_pages.append(st.Page(str(compliance_path), title="Compliance", icon="✅"))

# Create navigation with home page
pg = st.navigation([st.Page(home_page, title="Dashboard", icon="📊")] + all_pages)
pg.run()


