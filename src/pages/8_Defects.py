"""Defects page - uses universal template."""

import streamlit as st
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
from pages.universal_page_template import render_item_management_page

# Initialize core
dhf_root = Path(__file__).parent.parent.parent / "DHF"
core = CompliantFlowCore(dhf_root)

# Get doc type config
doc_type = None
for dt in core.config.doc_types:
    if dt.code == 'DEFECT':
        doc_type = dt
        break

if doc_type:
    # Convert to dict for template
    config_dict = {
        'code': doc_type.code,
        'name': doc_type.name,
        'prefix': doc_type.prefix,
        'icon': getattr(doc_type, 'icon', '🐛'),
        'lifecycle': getattr(doc_type, 'lifecycle', {}),
        'page_enabled': getattr(doc_type, 'page_enabled', True),
        'has_verification': getattr(doc_type, 'has_verification', False),
        'properties': doc_type.properties if hasattr(doc_type, 'properties') else [],
    }
    
    # Render page
    render_item_management_page(config_dict, core)
else:
    st.error("DEFECT doc type not found in project configuration")
