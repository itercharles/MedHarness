"""CompliantFlow - Medical Device Design History File Management System"""

import streamlit as st
import pandas as pd
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore

# Page Configuration
st.set_page_config(
    page_title="CompliantFlow",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Core
@st.cache_resource
def get_core():
    dhf_root = Path(__file__).resolve().parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)

try:
    core = get_core()
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# Main Page
st.title("📋 CompliantFlow")
st.markdown("### Medical Device Design History File Management")

st.markdown("""
Welcome to CompliantFlow, a comprehensive system for managing medical device design history files (DHF) 
with full traceability and compliance support.

### Quick Start

Use the sidebar to navigate to different sections:

- **📋 Document Management Pages**: Create and manage requirements, designs, and test cases
- **🔗 Traceability**: View configurable traceability matrices
- **🏗️ Architecture**: Review system architecture specifications
- **🛡️ Risk Management**: Manage risks and control measures

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
    # Get doc type from prefix
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
    st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("CompliantFlow - Ensuring regulatory compliance through systematic traceability")
