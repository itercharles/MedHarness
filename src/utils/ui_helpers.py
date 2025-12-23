"""UI helper utilities for Streamlit pages."""

import streamlit as st
from typing import Dict, List, Optional
import pandas as pd


def make_item_columns_clickable(df: pd.DataFrame) -> Dict:
    """
    Create column config to make item ID columns clickable.
    
    Args:
        df: DataFrame to configure
    
    Returns:
        Dictionary of column configurations for st.dataframe
    """
    column_config = {}
    
    for col in df.columns:
        # Check if column contains item IDs (has hyphen pattern like UC-001, CRS-001, etc.)
        if df[col].dtype == 'object':
            # Sample first non-null value
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            
            if sample and isinstance(sample, str) and '-' in sample:
                # This looks like an item ID column - make it a link
                column_config[col] = st.column_config.LinkColumn(
                    col,
                    help=f"Click to view {col} details",
                    display_text=r"(.*)",  # Show the full ID
                    validate=r"^[A-Z]+-\d+$",  # Validate item ID format
                )
    
    return column_config


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
