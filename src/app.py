"""CompliantFlow - Medical Device Design History File Management System"""

# Load environment variables from .env file FIRST
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import streamlit as st
import pandas as pd
from traceability.compliant_flow_core import CompliantFlowCore
from pages.page_generator import generate_doc_type_pages
from utils.ui_helpers import check_and_show_item_detail

# Initialize Core
# @st.cache_resource
def get_core():
    import os
    # Check for DHF_ROOT environment variable (used by tests)
    dhf_root_env = os.environ.get('DHF_ROOT')
    if dhf_root_env:
        dhf_root = Path(dhf_root_env)
    else:
        # Default to production DHF directory
        dhf_root = Path(__file__).resolve().parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)

try:
    core = get_core()
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# Generate dynamic pages for document types
doc_pages_data = generate_doc_type_pages(core)

# Create page objects
pages = {}

# Home page
def home_page():
    st.title("📋 CompliantFlow")
    st.markdown("### Medical Device Design History File Management")
    
    # Check for item detail query parameter
    if check_and_show_item_detail(core):
        st.markdown("---")
    
    st.markdown("""
    Welcome to CompliantFlow, a comprehensive system for managing medical device design history files (DHF) 
    with full traceability and compliance support.
    
    ### Quick Start
    
    Use the sidebar to navigate to different sections:
    
    - **📋 Document Management Pages**: Create and manage requirements, designs, and test cases
    - **🔗 Traceability**: View configurable traceability matrices
    - **✅ Compliance**: Validate against regulatory policies
    
    ### Key Features
    
    - ✅ **Full Traceability**: Configurable matrices showing requirement chains
    - ✅ **Lifecycle Management**: Track items through draft, review, and approval
    - ✅ **Compliance Ready**: Supports IEC 62304, ISO 14971, FDA 21 CFR 820
    - ✅ **Version Control**: Git-based change tracking
    - ✅ **PDF Export**: Generate regulatory-ready documentation
    
    ### Project Statistics
    """)
    
    # Display project statistics
    all_items = core.get_all_items()
    doc_types = {}
    for item in all_items:
        item_id = item['id']
        for dt in core.config.doc_types:
            if item_id.startswith(dt.prefix):
                doc_type = dt.code
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                break
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Items", len(all_items))
    with col2:
        st.metric("Document Types", len(doc_types))
    with col3:
        approved = len([i for i in all_items if i.get('status') == 'approved'])
        st.metric("Approved Items", approved)
    with col4:
        coverage = (approved / len(all_items) * 100) if all_items else 0
        st.metric("Approval Rate", f"{coverage:.0f}%")
    
    # Document type breakdown
    st.markdown("### Document Type Breakdown")
    breakdown_data = []
    for dt_code, count in sorted(doc_types.items()):
        dt_config = core.config.get_doc_type(dt_code)
        name = dt_config.name if dt_config else dt_code
        breakdown_data.append({"Type": name, "Count": count})
    
    if breakdown_data:
        st.dataframe(pd.DataFrame(breakdown_data), width="stretch", hide_index=True)
    
    st.markdown("---")
    st.caption("CompliantFlow - Ensuring regulatory compliance through systematic traceability")

# Build pages list
all_pages = []

# Home page
all_pages.append(st.Page(home_page, title="Home", icon="🏠", default=True))

# Add dynamic document type pages
for page_num, name, icon, func, code in doc_pages_data:
    all_pages.append(st.Page(func, title=name, icon=icon, url_path=f"{page_num}_{code}"))

# Add special pages
all_pages.append(st.Page("pages/02_Traceability.py", title="Traceability", icon="🔗"))
all_pages.append(st.Page("pages/03_Compliance.py", title="Compliance", icon="✅"))

# Configure navigation
pg = st.navigation(all_pages)
pg.run()
