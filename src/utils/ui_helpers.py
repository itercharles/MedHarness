"""UI helper utilities for Streamlit pages."""

import streamlit as st
from typing import Dict, List, Optional
import pandas as pd


def get_page_url_for_item(item_id: str, core=None) -> str:
    """
    Get the page URL for a given item ID.
    
    Args:
        item_id: Item ID (e.g., SYS-001, UC-002)
        core: Optional CompliantFlowCore instance for dynamic mapping
    
    Returns:
        Page URL with item selection parameter
    """
    # Extract document type from item ID
    doc_type_prefix = item_id.split('-')[0]
    
    # For test cases, extract the prefix (e.g., TC-SYS from TC-SYS-001)
    if item_id.startswith('TC-'):
        parts = item_id.split('-')
        if len(parts) >= 3:
            doc_type_prefix = f"{parts[0]}-{parts[1]}"
    
    # If core is provided, get page mapping from config
    if core:
        for doc_type in core.config.doc_types:
            if doc_type.prefix == doc_type_prefix or doc_type.code == doc_type_prefix:
                page_num = getattr(doc_type, 'page_number', None)
                if page_num and getattr(doc_type, 'page_enabled', False):
                    return f"/{page_num}_{doc_type.code}?item={item_id}"
    
    # Fallback: just use query param (will stay on current page)
    return f"?item={item_id}"


def make_item_columns_clickable(df: pd.DataFrame, core=None) -> tuple[pd.DataFrame, Dict]:
    """
    Create column config to make item ID columns clickable and transform IDs to URLs.
    
    Args:
        df: DataFrame to configure
        core: Optional CompliantFlowCore instance for dynamic page mapping
    
    Returns:
        Tuple of (transformed dataframe, column config dictionary)
    """
    if df.empty:
        return df, {}
    
    # Create a copy to avoid modifying original
    df_copy = df.copy()
    column_config = {}
    
    for col in df.columns:
        # Check if column contains item IDs (has hyphen pattern like UC-001, CRS-001, etc.)
        if df[col].dtype == 'object':
            # Sample first non-null value
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            
            if sample and isinstance(sample, str) and '-' in sample:
                # This looks like an item ID column - convert to page URLs
                df_copy[col] = df[col].apply(
                    lambda x: get_page_url_for_item(x, core) if isinstance(x, str) and '-' in x else x
                )
                
                # Configure as link column
                column_config[col] = st.column_config.LinkColumn(
                    col,
                    help=f"Click to view {col} on its page",
                    display_text=r".*item=([^&]+)",  # Extract and show just the ID
                )
    
    return df_copy, column_config


def check_and_show_item_detail(core):
    """
    Check for item query parameter and show detail if present.
    
    Args:
        core: CompliantFlowCore instance
    
    Returns:
        Item ID if present, None otherwise
    """
    # Check for item query parameter
    if "item" in st.query_params:
        item_id = st.query_params["item"]
        
        item = core.get_item(item_id)
        
        if not item:
            st.error(f"Item {item_id} not found")
            return None
        
        # Show item detail in expander
        with st.expander(f"📄 {item_id} - {item.get('title', 'Untitled')}", expanded=True):
            # Basic info
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**ID:** {item['id']}")
                st.write(f"**Title:** {item.get('title', 'N/A')}")
                st.write(f"**Status:** {item.get('status', 'N/A')}")
            
            with col2:
                st.write(f"**Type:** {item['id'].split('-')[0]}")
                if item.get('reviewer'):
                    st.write(f"**Reviewer:** {item['reviewer']}")
                if item.get('review_date'):
                    st.write(f"**Review Date:** {item['review_date']}")
            
            # Content
            st.write("**Content:**")
            st.write(item.get('content', 'N/A'))
            
            # Relationships
            all_links = item.get('all_links', {})
            if all_links and any(links for links in all_links.values()):
                st.write("---")
                st.write("**Relationships:**")
                
                for rel_type, linked_uids in all_links.items():
                    if linked_uids:
                        rel_label = rel_type.replace('_', ' ').title()
                        st.write(f"*{rel_label}:* {', '.join(linked_uids)}")
        
        # Add clear button
        if st.button("✖ Close Item Detail"):
            del st.query_params["item"]
            st.rerun()
        
        return item_id
    
    return None
