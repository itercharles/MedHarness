"""Dynamic page generator for document types."""

from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore
import streamlit as st

def create_doc_page_function(doc_type, core):
    """Create a page function for a specific document type."""
    def page_func():
        from pages.universal_page_template import render_item_management_page
        
        config_dict = {
            'code': doc_type.code,
            'name': doc_type.name,
            'prefix': doc_type.prefix,
            'icon': getattr(doc_type, 'icon', '📄'),
            'lifecycle': getattr(doc_type, 'lifecycle', {}),
            'page_enabled': True,
            'has_verification': getattr(doc_type, 'has_verification', False),
            'properties': doc_type.properties if hasattr(doc_type, 'properties') else [],
        }
        render_item_management_page(config_dict, core)
    
    # Set unique function name to avoid URL conflicts
    page_func.__name__ = f"page_{doc_type.code}"
    
    return page_func


def generate_doc_type_pages(core: CompliantFlowCore):
    """Generate Streamlit pages for all enabled document types.
    
    Returns:
        List of tuples (page_number, st.Page) sorted by page number
    """
    pages = []
    
    for doc_type in core.config.doc_types:
        # Skip if page not enabled
        if not getattr(doc_type, 'page_enabled', False):
            continue
        
        page_number = getattr(doc_type, 'page_number', 99)
        icon = getattr(doc_type, 'icon', '📄')
        
        # Create page function
        page_func = create_doc_page_function(doc_type, core)
        
        # Store with page number for sorting
        pages.append((page_number, doc_type.name, icon, page_func, doc_type.code))
    
    # Sort by page number
    pages.sort(key=lambda x: x[0])
    
    return pages
