"""Reusable UI components for CompliantFlow Streamlit app."""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Callable


def render_manual_verification(
    criterion: Dict[str, Any],
    item_id: str,
    current_verifications: Dict[str, Dict[str, Any]],
    on_verify: Callable[[str, str, str, str], None]
) -> None:
    """
    Render a manual verification expander for a criterion.
    
    Args:
        criterion: Criterion dictionary with id, name, description
        item_id: Unique ID for the item being verified (e.g., release version)
        current_verifications: Dict of existing verifications
        on_verify: Callback function(criterion_id, verifier, notes, item_id) called when verified
    """
    criterion_id = criterion.get('id')
    criterion_name = criterion.get('name')
    criterion_desc = criterion.get('description')
    
    # Check if already verified
    if criterion_id in current_verifications:
        verification = current_verifications[criterion_id]
        verified_by = verification.get('verified_by', 'Unknown')
        verified_date = verification.get('verified_date', '')
        notes = verification.get('notes', '')
        
        st.success(f"✅ {criterion_name}: Verified by {verified_by}")
        if notes:
            with st.expander("View verification notes"):
                st.write(notes)
                st.caption(f"Verified on: {verified_date}")
    else:
        # Show verification expander
        with st.expander(f"⚠️ {criterion_name} - Click to verify", expanded=False):
            st.write(f"**Description:** {criterion_desc}")
            
            verifier = st.text_input(
                "Verified by *",
                key=f"verifier_{item_id}_{criterion_id}",
                placeholder="Enter your name"
            )
            notes = st.text_area(
                "Verification notes (optional)",
                key=f"notes_{item_id}_{criterion_id}",
                height=80,
                placeholder="Add any relevant notes about this verification..."
            )
            
            if st.button(
                f"✓ Confirm Verification",
                key=f"confirm_{item_id}_{criterion_id}",
                type="primary"
            ):
                if verifier:
                    # Call the verification callback
                    on_verify(criterion_id, verifier, notes, item_id)
                else:
                    st.error("Please enter verifier name")


def render_stage_approval(
    stage_name: str,
    item_id: str,
    on_approve: Callable[[str, str], None],
    button_text: str = "Approve & Continue"
) -> None:
    """
    Render a stage approval form.
    
    Args:
        stage_name: Name of the stage transition (e.g., "planning_to_developing")
        item_id: Unique ID for the item (e.g., release version)
        on_approve: Callback function(approver, item_id) called when approved
        button_text: Text for the approval button
    """
    st.markdown("---")
    st.markdown("**Stage Transition Approval:**")
    
    approver = st.text_input(
        "Approved by *",
        key=f"approver_{stage_name}_{item_id}",
        placeholder="Enter approver name"
    )
    
    if st.button(button_text, key=f"approve_btn_{stage_name}_{item_id}", type="primary"):
        if approver:
            on_approve(approver, item_id)
        else:
            st.warning("Please enter approver name")


def render_criteria_checklist(
    criteria_results: list,
    item_id: str,
    current_verifications: Dict[str, Dict[str, Any]],
    on_verify: Callable[[str, str, str, str], None]
) -> None:
    """
    Render a complete criteria checklist with manual verifications.
    
    Args:
        criteria_results: List of criterion result dictionaries
        item_id: Unique ID for the item being verified
        current_verifications: Dict of existing manual verifications
        on_verify: Callback for manual verifications
    """
    for criterion in criteria_results:
        severity = criterion.get('severity', 'error')
        check_type = criterion.get('check_type')
        
        if criterion['passed']:
            st.success(f"✅ {criterion['name']}: {criterion['message']}")
        elif check_type == 'manual':
            # Use the reusable manual verification component
            render_manual_verification(
                criterion,
                item_id,
                current_verifications,
                on_verify
            )
        elif severity == 'warning':
            st.warning(f"⚠️ {criterion['name']}: {criterion['message']}")
        else:
            st.error("❌ {criterion['name']}: {criterion['message']}")


def render_status_badge(status: str, verification_status: str = None) -> None:
    """
    Render status badge with color coding.
    
    Args:
        status: Lifecycle status (draft, approved, retired)
        verification_status: Verification status (not_verified, verified, failed)
    """
    # Lifecycle status
    if status == "approved":
        st.success(f"✅ {status.upper()}")
    elif status == "retired":
        st.info(f"🔒 {status.upper()}")
    else:  # draft
        st.warning(f"📝 {status.upper()}")
    
    # Verification status (if provided)
    if verification_status:
        if verification_status == "verified":
            st.success(f"✓ Verified")
        elif verification_status == "failed":
            st.error(f"✗ Verification Failed")
        else:
            st.info(f"○ Not Verified")


def render_item_card(
    item: Dict[str, Any],
    item_type: str,
    core: Any,
    show_actions: bool = True
) -> None:
    """
    Render expandable card for any item type.
    
    Args:
        item: Item dictionary
        item_type: Type prefix (CRS, SYS, SDS, etc.)
        core: CompliantFlowCore instance
        show_actions: Whether to show action buttons
    """
    with st.expander(f"▼ {item['id']} - {item.get('title', 'N/A')}", expanded=False):
        # Status badges
        col1, col2 = st.columns(2)
        with col1:
            render_status_badge(
                item.get('status', 'draft'),
                item.get('verification_status')
            )
        with col2:
            if item.get('approved_by'):
                st.write(f"**Approved by:** {item['approved_by']}")
                if item.get('approved_date'):
                    st.caption(f"on {item['approved_date']}")
        
        # Content
        st.markdown(f"**Content:** {item.get('content', 'N/A')}")
        
        # Traceability links
        if item.get('links'):
            st.markdown("**Linked Items:**")
            for link_id in item['links']:
                linked_item = core.get_item(link_id)
                if linked_item:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        link_status = linked_item.get('status', 'unknown')
                        status_icon = "✅" if link_status == "approved" else "📝"
                        st.write(f"{status_icon} → {link_id}: {linked_item.get('title', 'N/A')}")
                    with col2:
                        if st.button("View", key=f"view_link_{item['id']}_{link_id}"):
                            st.session_state['selected_item'] = link_id
                            st.rerun()
        
        # Actions
        if show_actions:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Edit", key=f"edit_{item['id']}", use_container_width=True):
                    st.session_state['edit_item'] = item['id']
                    st.rerun()
            with col2:
                if item.get('status') == 'draft':
                    if st.button("Approve", key=f"approve_{item['id']}", type="primary", use_container_width=True):
                        st.session_state['approve_item'] = item['id']
                        st.rerun()
            with col3:
                if item.get('status') == 'approved':
                    if st.button("Retire", key=f"retire_{item['id']}", use_container_width=True):
                        st.session_state['retire_item'] = item['id']
                        st.rerun()

