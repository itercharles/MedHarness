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


def render_status_badge(status: str, state_config: Dict[str, Any] = None, verification_status: str = None) -> None:
    """
    Render status badge with color coding.
    
    Args:
        status: Lifecycle status
        state_config: State configuration dict with 'color' and 'icon' fields
        verification_status: Verification status (PASS, FAIL, PENDING)
    """
    # Lifecycle status
    if state_config:
        color_map = {
            'success': st.success,
            'warning': st.warning,
            'error': st.error,
            'info': st.info,
            'secondary': st.info
        }
        color = state_config.get('color', 'secondary')
        icon = state_config.get('icon', '📄')
        label = state_config.get('label', status.upper())
        
        render_func = color_map.get(color, st.info)
        render_func(f"{icon} {label}")
    else:
        # Fallback if no config provided
        st.info(f"📄 {status.upper()}")
    
    # Verification status (if provided)
    if verification_status:
        if verification_status == "PASS":
            st.success(f"✓ Verified")
        elif verification_status == "FAIL":
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
            current_status = item.get('status', 'unknown')
            state_config = None
            if True:  # Always use core
                state_config = core.get_state_info(current_status)
            
            render_status_badge(
                current_status,
                state_config,
                item.get('verification_status')
            )
        with col2:
            # Show metadata for current state (e.g., approved_by, approved_date)
            status = item.get('status', '')
            by_field = f"{status}_by"
            date_field = f"{status}_date"
            
            if item.get(by_field):
                st.write(f"**{status.capitalize()} by:** {item[by_field]}")
                if item.get(date_field):
                    st.caption(f"on {item[date_field]}")
        
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
                        # Get state config for linked item to show appropriate icon
                        link_icon = '📄'
                        if True:  # Always use core
                            link_state = core.get_state_info(link_status)
                            link_icon = link_state.get('icon', '📄')
                        st.write(f"{link_icon} → {link_id}: {linked_item.get('title', 'N/A')}")
                    with col2:
                        if st.button("View", key=f"view_link_{item['id']}_{link_id}"):
                            st.session_state['selected_item'] = link_id
                            st.rerun()
        
        # Actions - show available transitions
        if show_actions and workflow_engine:
            current_status = item.get('status', core.get_initial_state(item["id"].split("-")[0]))
            available_transitions = core.get_available_transitions(item)
            
            if available_transitions:
                st.markdown("---")
                cols = st.columns(len(available_transitions))
                for idx, transition in enumerate(available_transitions):
                    with cols[idx]:
                        if st.button(
                            transition['label'],
                            key=f"transition_{item['id']}_{transition['to']}",
                            type="primary" if idx == 0 else "secondary",
                            use_container_width=True
                        ):
                            st.session_state['transition_item'] = item
                            st.session_state['transition_config'] = transition
                            st.rerun()

