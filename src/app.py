"""CompliantFlow - Medical Device Design History File Management System"""

# Load environment variables from .env file FIRST
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import streamlit as st
import pandas as pd
import yaml
from traceability.compliant_flow_core import CompliantFlowCore
from pages.page_generator import generate_doc_type_pages
from utils.ui_helpers import check_and_show_item_detail


def get_dhf_root(config_file: str = None) -> Path:
    """
    Get DHF root directory from configuration.
    
    Args:
        config_file: Path to app_config.yaml (optional)
        
    Returns:
        Path to DHF directory
    """
    # Default to production DHF
    default_dhf = Path(__file__).resolve().parent.parent / "DHF"
    
    # If no config file specified, use default location
    if config_file is None:
        config_file = Path(__file__).resolve().parent.parent / "app_config.yaml"
    else:
        config_file = Path(config_file)
    
    # If config file doesn't exist, use default
    if not config_file.exists():
        return default_dhf
    
    # Read config file
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
        
        if 'dhf_root' in config_data:
            dhf_path = config_data['dhf_root']
            # Resolve relative paths from project root
            if not Path(dhf_path).is_absolute():
                project_root = Path(__file__).resolve().parent.parent
                return project_root / dhf_path
            return Path(dhf_path)
    except Exception as e:
        st.warning(f"Failed to load config file {config_file}: {e}. Using default DHF.")
    
    return default_dhf


# Initialize Core
@st.cache_resource
def get_core(_config_file: str = None):
    """
    Initialize CompliantFlowCore with DHF from configuration.
    
    Args:
        _config_file: Path to app_config.yaml (optional, prefixed with _ for st.cache)
    """
    dhf_root = get_dhf_root(_config_file)
    return CompliantFlowCore(dhf_root)


# Get config file path (use default location)
config_file = None  # Will use default app_config.yaml location

try:
    core = get_core(config_file)
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# Configure page
st.set_page_config(
    page_title="CompliantFlow",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
all_items = core.get_all_items()

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

# Generate dynamic pages for each document type
all_pages = generate_doc_type_pages(core)

# Add static pages with absolute paths
src_dir = Path(__file__).parent
all_pages.append(st.Page(str(src_dir / "pages" / "01_Dashboard.py"), title="Dashboard", icon="📊"))
all_pages.append(st.Page(str(src_dir / "pages" / "02_Traceability.py"), title="Traceability", icon="🔗"))
all_pages.append(st.Page(str(src_dir / "pages" / "03_Compliance.py"), title="Compliance", icon="✅"))

# Configure navigation
pg = st.navigation(all_pages)
pg.run()
