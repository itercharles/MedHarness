"""Universal item management page template - works for all item types via configuration."""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from traceability.compliant_flow_core import CompliantFlowCore
from traceability.workflow_engine import DynamicWorkflowEngine
from ui_components import (
    render_manual_verification,
    render_status_badge
)


def render_item_management_page(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore
) -> None:
    """
    Universal item management page template.
    Works for ALL item types through project configuration.
    
    Args:
        doc_type_config: Doc type configuration from project_config.yaml
        core: CompliantFlowCore instance
    """
    # Extract config
    code = doc_type_config['code']
    name = doc_type_config['name']
    prefix = doc_type_config['prefix']
    icon = doc_type_config.get('icon', '📄')
    lifecycle = doc_type_config.get('lifecycle', {})
    
    # Page setup
    st.set_page_config(page_title=name, page_icon=icon, layout="wide")
    st.title(f"{icon} {name}")
    
    # Initialize workflow engine
    workflow_engine = DynamicWorkflowEngine(doc_type_config, core)
    
    # === METRICS (below title) ===
    render_metrics(doc_type_config, core, prefix)
    
    st.markdown("---")
    
    # === TABLE SECTION (top) ===
    render_table_section(doc_type_config, core, workflow_engine, prefix)
    
    st.markdown("---")
    
    # === DETAIL PANEL (bottom) ===
    render_detail_panel(doc_type_config, core, workflow_engine)


def render_metrics(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    prefix: str
) -> None:
    """Render metrics below title."""
    all_items = core.get_all_items()
    type_items = [
        item for item in all_items
        if item['id'].startswith(prefix.rstrip('-'))
    ]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(type_items))
    with col2:
        approved = len([i for i in type_items if i.get('status') == 'approved'])
        st.metric("Approved", approved)
    with col3:
        draft = len([i for i in type_items if i.get('status') == 'draft'])
        st.metric("Draft", draft)
    with col4:
        if doc_type_config.get('has_verification'):
            verified = len([i for i in type_items if i.get('verification_status') == 'verified'])
            st.metric("Verified", verified)



def render_table_section(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine,
    prefix: str
) -> None:
    """Render table section with New button and filters."""
    # Header with Export and New buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader("Items")
    with col2:
        if st.button("📄 Export PDF", use_container_width=True):
            # Generate PDF
            try:
                from pathlib import Path
                from traceability.document_generator import DocumentGenerator
                
                template_dir = Path(core.repo_root) / "templates"
                generator = DocumentGenerator(core, template_dir)
                
                doc_type_code = doc_type_config['code']
                pdf_path = generator.generate_requirements_spec(doc_type_code)
                
                # Provide download
                with open(pdf_path, 'rb') as f:
                    st.download_button(
                        label=f"⬇️ Download {doc_type_code} Specification",
                        data=f.read(),
                        file_name=f"{doc_type_code}_Specification.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                st.success(f"✅ Generated {doc_type_code} specification PDF!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
    with col3:
        if st.button("➕ New", type="primary", use_container_width=True):
            st.session_state['creating_new'] = True
            st.session_state['selected_item_id'] = None
            st.rerun()
    
    # Filters
    lifecycle = doc_type_config.get('lifecycle', {})
    states = lifecycle.get('states', [])
    state_ids = [s['id'] for s in states]
    
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Status",
            state_ids,
            default=state_ids[:2] if len(state_ids) >= 2 else state_ids,
            key="status_filter"
        )
    with col2:
        search = st.text_input("Search", placeholder="Search by ID or title...", key="search_filter")
    
    # Get and filter items
    all_items = core.get_all_items()
    filtered_items = []
    for item in all_items:
        if not item['id'].startswith(prefix.rstrip('-')):
            continue
        item_status = item.get('status', workflow_engine.get_initial_state())
        if item_status not in status_filter:
            continue
        if search:
            search_lower = search.lower()
            if search_lower not in item['id'].lower() and search_lower not in item.get('title', '').lower():
                continue
        filtered_items.append(item)
    
    # Display table
    if not filtered_items:
        st.info(f"No {doc_type_config['name'].lower()} found matching filters")
    else:
        # Create clickable table
        df_data = []
        for item in filtered_items:
            # Format links as comma-separated string
            links_str = ', '.join(item.get('links', [])) if item.get('links') else ''
            
            df_data.append({
                'ID': item['id'],
                'Title': item.get('title', 'N/A'),
                'Status': item.get('status', workflow_engine.get_initial_state()),
                'Links': links_str
            })
        
        df = pd.DataFrame(df_data)
        
        # Use dataframe with on_click selection (no checkboxes)
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="items_table"
        )
        
        # Handle row selection
        if event.selection and event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_item_id = filtered_items[selected_idx]['id']
            if st.session_state.get('selected_item_id') != selected_item_id:
                st.session_state['selected_item_id'] = selected_item_id
                st.session_state['creating_new'] = False
                st.rerun()


def render_detail_panel(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render detail panel for selected item or new item creation."""
    # Check if creating new
    if st.session_state.get('creating_new'):
        render_new_item_form(doc_type_config, core, workflow_engine)
        return
    
    # Check if item selected
    selected_item_id = st.session_state.get('selected_item_id')
    if not selected_item_id:
        st.info("👆 Select an item from the table above to view details")
        return
    
    # Load and display item
    item = core.get_item(selected_item_id)
    if not item:
        st.error(f"Item {selected_item_id} not found")
        return
    
    render_item_details(item, doc_type_config, core, workflow_engine)


def render_new_item_form(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render form for creating new item."""
    st.subheader(f"➕ New {doc_type_config['name']}")
    
    # Get properties from config
    properties = doc_type_config.get('properties', [])
    
    # Form fields - dynamically generate based on properties
    form_data = {}
    
    # ID (always required)
    form_data['id'] = st.text_input("ID *", placeholder=f"{doc_type_config['prefix']}XXX", key="new_id")
    
    # Other properties
    for prop in properties:
        if prop == 'id':
            continue  # Already handled
        elif prop == 'status':
            continue  # Set automatically
        elif prop == 'title':
            form_data['title'] = st.text_input("Title *", key="new_title")
        elif prop == 'content':
            form_data['content'] = st.text_area("Content *", height=150, key="new_content")
        elif prop == 'links':
            # Multi-select for links
            all_items = core.get_all_items()
            link_options = [item['id'] for item in all_items]
            form_data['links'] = st.multiselect("Links", link_options, key="new_links")
        elif prop in ['user_group', 'source', 'category', 'component', 'type']:
            # Text input for string fields
            form_data[prop] = st.text_input(prop.replace('_', ' ').title(), key=f"new_{prop}")
        elif prop in ['verification_method', 'critical_safety']:
            # Special fields
            if prop == 'verification_method':
                form_data[prop] = st.selectbox(
                    "Verification Method",
                    ["Test", "Analysis", "Inspection", "Demonstration"],
                    key="new_verification_method"
                )
            elif prop == 'critical_safety':
                form_data[prop] = st.checkbox("Critical Safety", key="new_critical_safety")
        elif prop in ['hazard', 'cause', 'effect', 'severity_pre', 'probability_pre']:
            # Risk-specific fields
            if prop in ['hazard', 'cause', 'effect']:
                form_data[prop] = st.text_area(prop.title(), height=100, key=f"new_{prop}")
            else:
                form_data[prop] = st.selectbox(
                    prop.replace('_', ' ').title(),
                    ["Low", "Medium", "High"],
                    key=f"new_{prop}"
                )
        elif prop in ['prerequisites', 'steps', 'expected_result']:
            # Test case fields
            form_data[prop] = st.text_area(prop.replace('_', ' ').title(), height=100, key=f"new_{prop}")
        # Skip metadata fields that are set automatically
        elif prop not in ['reviewer', 'review_date', 'approved_by', 'approved_date', 
                          'retired_by', 'retired_date', 'manual_verifications', 
                          'verification_status', 'verified_by', 'verified_date']:
            # Generic text input for any other field
            form_data[prop] = st.text_input(prop.replace('_', ' ').title(), key=f"new_{prop}")
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Create", type="primary", use_container_width=True, key="create_btn"):
            # Validate required fields
            if not form_data.get('id'):
                st.error("ID is required")
            elif not form_data.get('title'):
                st.error("Title is required")
            elif not form_data.get('content'):
                st.error("Content is required")
            else:
                # Create new item with all filled fields
                new_item = {
                    'id': form_data['id'],
                    'status': workflow_engine.get_initial_state(),
                }
                
                # Add all other fields that have values
                for key, value in form_data.items():
                    if key != 'id' and value:  # Skip empty values
                        new_item[key] = value
                
                # Ensure links is a list
                if 'links' not in new_item:
                    new_item['links'] = []
                
                # Save item
                try:
                    core.update_item(form_data['id'], new_item)
                    st.success(f"✅ Created {form_data['id']}")
                    
                    # Clear creation mode and select new item
                    st.session_state['creating_new'] = False
                    st.session_state['selected_item_id'] = form_data['id']
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating item: {str(e)}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key="cancel_btn"):
            st.session_state['creating_new'] = False
            st.rerun()



def render_item_details(
    item: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render detailed view of selected item with workflow actions."""
    
    # Check if in edit mode
    is_editing = st.session_state.get('editing_item_id') == item['id']
    
    if is_editing:
        render_item_edit_form(item, doc_type_config, core, workflow_engine)
    else:
        render_item_view(item, doc_type_config, core, workflow_engine)


def render_item_view(
    item: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render read-only view of item details."""
    # Header with Edit button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{item['id']} - {item.get('title', 'N/A')}")
    with col2:
        if st.button("✏️ Edit", use_container_width=True, key=f"edit_{item['id']}"):
            st.session_state['editing_item_id'] = item['id']
            st.rerun()
    
    # Status and metadata in columns
    current_state = item.get('status', workflow_engine.get_initial_state())
    state_info = workflow_engine.get_state_info(current_state)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Status:** {state_info['icon']} {state_info['label']}")
    with col2:
        if item.get('approved_by'):
            st.markdown(f"**Approved by:** {item['approved_by']}")
        if item.get('approved_date'):
            st.markdown(f"**Approved:** {item['approved_date'][:10]}")
    
    # Get properties from config to show all fields
    properties = doc_type_config.get('properties', [])
    
    # Fields to skip (system/internal fields)
    skip_fields = {'id', 'status', 'approved_by', 'approved_date', 'retired_by', 
                   'retired_date', 'manual_verifications', 'history', 'links',
                   'active', 'reviewer', 'review_date', 'verified_by', 'verified_date'}
    
    # Display all configured fields
    for prop in properties:
        if prop in skip_fields:
            continue
        
        # Get value from item
        value = item.get(prop)
        
        # Format field name with better styling
        field_name = prop.replace('_', ' ').title()
        
        # Display field with visual distinction
        if isinstance(value, list):
            st.markdown(f"**{field_name}:**")
            if value:
                for v in value:
                    st.markdown(f"  - {v}")
            else:
                st.caption("  _(empty)_")
        elif isinstance(value, bool):
            st.markdown(f"**{field_name}:** {'✅ Yes' if value else '❌ No'}")
        elif value is None or value == '':
            st.markdown(f"**{field_name}:**")
            st.caption("  _(not set)_")
        else:
            # String or other simple types
            if len(str(value)) > 100:
                st.markdown(f"**{field_name}:**")
                st.text_area(field_name, value, height=100, disabled=True, key=f"field_{prop}_{item['id']}", label_visibility="collapsed")
            else:
                st.markdown(f"**{field_name}:** `{value}`")
    
    # Links section (shown separately for better formatting)
    if item.get('links'):
        st.markdown("**Linked Items:**")
        for link_id in item['links']:
            linked_item = core.get_item(link_id)
            if linked_item:
                link_status = linked_item.get('status', 'unknown')
                st.markdown(f"  - **{link_id}**: {linked_item.get('title', 'N/A')} _{({link_status})}_")
            else:
                st.markdown(f"  - **{link_id}** _(not found)_")


def render_item_edit_form(
    item: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render editable form for item."""
    st.subheader(f"✏️ Edit {item['id']}")
    
    # Get properties from config
    properties = doc_type_config.get('properties', [])
    
    # Form fields - dynamically generate based on properties
    form_data = {}
    
    # Fields to skip (system/internal fields)
    skip_fields = {'id', 'status', 'approved_by', 'approved_date', 'retired_by', 
                   'retired_date', 'manual_verifications', 'history',
                   'active', 'reviewer', 'review_date', 'verified_by', 'verified_date'}
    
    # Display all editable fields
    for prop in properties:
        if prop in skip_fields:
            continue
        
        # Get current value
        current_value = item.get(prop, '')
        field_name = prop.replace('_', ' ').title()
        
        # Render appropriate input based on property
        if prop == 'title':
            form_data['title'] = st.text_input("Title *", value=current_value, key=f"edit_title_{item['id']}")
        elif prop == 'content':
            form_data['content'] = st.text_area("Content *", value=current_value, height=150, key=f"edit_content_{item['id']}")
        elif prop == 'links':
            all_items = core.get_all_items()
            link_options = [i['id'] for i in all_items if i['id'] != item['id']]
            form_data['links'] = st.multiselect("Links", link_options, default=current_value if current_value else [], key=f"edit_links_{item['id']}")
        elif prop in ['user_group', 'source', 'category', 'component', 'type']:
            form_data[prop] = st.text_input(field_name, value=current_value if current_value else '', key=f"edit_{prop}_{item['id']}")
        elif prop == 'verification_method':
            methods = ["Test", "Analysis", "Inspection", "Demonstration"]
            default_idx = methods.index(current_value) if current_value in methods else 0
            form_data[prop] = st.selectbox("Verification Method", methods, index=default_idx, key=f"edit_vm_{item['id']}")
        elif prop == 'critical_safety':
            form_data[prop] = st.checkbox("Critical Safety", value=bool(current_value), key=f"edit_cs_{item['id']}")
        elif prop in ['hazard', 'cause', 'effect']:
            form_data[prop] = st.text_area(field_name, value=current_value if current_value else '', height=100, key=f"edit_{prop}_{item['id']}")
        elif prop in ['severity_pre', 'probability_pre']:
            levels = ["Low", "Medium", "High"]
            default_idx = levels.index(current_value) if current_value in levels else 0
            form_data[prop] = st.selectbox(field_name, levels, index=default_idx, key=f"edit_{prop}_{item['id']}")
        elif prop in ['prerequisites', 'steps', 'expected_result']:
            form_data[prop] = st.text_area(field_name, value=current_value if current_value else '', height=100, key=f"edit_{prop}_{item['id']}")
        else:
            # Generic text input
            form_data[prop] = st.text_input(field_name, value=current_value if current_value else '', key=f"edit_{prop}_{item['id']}")
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save", type="primary", use_container_width=True, key=f"save_edit_{item['id']}"):
            # Validate required fields
            if not form_data.get('title'):
                st.error("Title is required")
            elif not form_data.get('content'):
                st.error("Content is required")
            else:
                # Update item with edited values
                updated_item = item.copy()
                
                # Update all fields
                for key, value in form_data.items():
                    if value or value == False:  # Include False for booleans
                        updated_item[key] = value
                    elif key in updated_item:
                        # Remove field if cleared
                        del updated_item[key]
                
                # Ensure links is a list
                if 'links' not in updated_item:
                    updated_item['links'] = []
                
                # Save item
                try:
                    core.update_item(item['id'], updated_item)
                    st.success(f"✅ Saved {item['id']}")
                    del st.session_state['editing_item_id']
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving item: {str(e)}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_edit_{item['id']}"):
            del st.session_state['editing_item_id']
            st.rerun()
    
    # Workflow actions
    current_state = item.get('status', workflow_engine.get_initial_state())
    available_transitions = workflow_engine.get_available_transitions(current_state)
    
    if available_transitions:
        st.markdown("**Available Actions:**")
        cols = st.columns(len(available_transitions))
        for idx, transition in enumerate(available_transitions):
            with cols[idx]:
                button_type = transition.get('button_type', 'secondary')
                if st.button(
                    transition['label'],
                    key=f"action_{item['id']}_{transition['to']}",
                    type=button_type,
                    use_container_width=True
                ):
                    st.session_state['transition_item'] = item['id']
                    st.session_state['transition_config'] = transition
                    st.rerun()
    
    # Handle workflow transition
    if (st.session_state.get('transition_item') == item['id'] and 
        'transition_config' in st.session_state):
        st.markdown("---")
        render_transition_workflow(
            item,
            st.session_state['transition_config'],
            doc_type_config,
            core,
            workflow_engine
        )


def render_transition_workflow(
    item: Dict[str, Any],
    transition: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render workflow transition with criteria checking."""
    st.markdown(f"### {transition['label']}")
    
    # Check criteria
    can_transition, criteria_results = workflow_engine.check_transition_criteria(item, transition)
    
    # Show criteria
    st.markdown("**Criteria:**")
    for criterion in criteria_results:
        if criterion['passed']:
            st.success(f"✅ {criterion['name']}")
        else:
            if criterion['check_type'] == 'manual':
                # Manual verification UI
                with st.expander(f"⚠️ {criterion['name']} - Verification Required", expanded=True):
                    verifier = st.text_input("Verified by *", key=f"ver_{criterion['id']}")
                    notes = st.text_area("Notes", key=f"notes_{criterion['id']}", height=100)
                    if st.button("✅ Verify", key=f"btn_ver_{criterion['id']}"):
                        if verifier:
                            if 'manual_verifications' not in item:
                                item['manual_verifications'] = {}
                            item['manual_verifications'][criterion['id']] = {
                                'verified_by': verifier,
                                'verified_date': datetime.now().isoformat(),
                                'notes': notes
                            }
                            core.update_item(item['id'], item)
                            st.toast(f"✅ Verified by {verifier}")
                            st.rerun()
            else:
                st.error(f"❌ {criterion['name']}: {criterion['message']}")
    
    # Transition form
    if can_transition:
        st.markdown("---")
        metadata = {}
        
        if transition['to'] == 'approved':
            approver = st.text_input("Approved by *", key=f"approver_{item['id']}")
            if approver:
                metadata['approved_by'] = approver
                metadata['approved_date'] = datetime.now().isoformat()
        elif transition['to'] == 'retired':
            retired_by = st.text_input("Retired by *", key=f"retired_{item['id']}")
            if retired_by:
                metadata['retired_by'] = retired_by
                metadata['retired_date'] = datetime.now().isoformat()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ {transition['label']}", type="primary", use_container_width=True, key="confirm_transition"):
                if transition['to'] == 'approved' and not metadata.get('approved_by'):
                    st.warning("Please enter approver name")
                elif transition['to'] == 'retired' and not metadata.get('retired_by'):
                    st.warning("Please enter name")
                else:
                    metadata['timestamp'] = datetime.now().isoformat()
                    updated_item = workflow_engine.perform_transition(item, transition, metadata)
                    core.update_item(item['id'], updated_item)
                    st.success(f"✅ {item['id']} transitioned to {transition['to']}")
                    del st.session_state['transition_item']
                    del st.session_state['transition_config']
                    st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True, key="cancel_transition"):
                del st.session_state['transition_item']
                del st.session_state['transition_config']
                st.rerun()
    else:
        st.warning("⚠️ All required criteria must be met")
        if st.button("Cancel", key="cancel_criteria"):
            del st.session_state['transition_item']
            del st.session_state['transition_config']
            st.rerun()


def render_transition_dialog(
    item_id: str,
    transition: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Legacy function - redirects to render_transition_workflow."""
    item = core.get_item(item_id)
    if item:
        render_transition_workflow(item, transition, doc_type_config, core, workflow_engine)


def render_manual_verification_inline(
    criterion: Dict[str, Any],
    item_id: str,
    current_verifications: Dict[str, Dict[str, Any]],
    core: CompliantFlowCore
) -> None:
    """Render inline manual verification UI."""
    criterion_id = criterion['id']
    
    with st.expander(f"⚠️ {criterion['name']} - Manual Verification Required", expanded=True):
        if criterion.get('description'):
            st.info(criterion['description'])
        
        verifier = st.text_input(
            "Verified by *",
            key=f"verifier_{item_id}_{criterion_id}"
        )
        notes = st.text_area(
            "Notes",
            key=f"notes_{item_id}_{criterion_id}",
            height=100
        )
        
        if st.button("✅ Verify", key=f"verify_{item_id}_{criterion_id}"):
            if verifier:
                # Save verification
                item = core.get_item(item_id)
                if 'manual_verifications' not in item:
                    item['manual_verifications'] = {}
                
                item['manual_verifications'][criterion_id] = {
                    'verified_by': verifier,
                    'verified_date': datetime.now().isoformat(),
                    'notes': notes
                }
                
                core.update_item(item_id, item)
                st.toast(f"✅ Verified by {verifier}", icon="✅")
                st.rerun()
            else:
                st.warning("Please enter verifier name")



def render_items_table(
    items: list,
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render items as table."""
    if not items:
        st.info(f"No {doc_type_config['name'].lower()} found matching filters")
        return
    
    # Create dataframe
    df_data = []
    for item in items:
        df_data.append({
            'ID': item['id'],
            'Title': item.get('title', 'N/A'),
            'Status': item.get('status', workflow_engine.get_initial_state()),
            'Verified': item.get('verification_status', 'not_verified'),
            'Links': len(item.get('links', []))
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Action buttons for each item
    st.markdown("**Actions:**")
    for item in items:
        render_item_actions(item, doc_type_config, core, workflow_engine)


def render_item_actions(
    item: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render action buttons for an item."""
    current_state = item.get('status', workflow_engine.get_initial_state())
    available_transitions = workflow_engine.get_available_transitions(current_state)
    
    # Calculate number of columns needed
    num_cols = 3 + len(available_transitions)
    cols = st.columns([3] + [1] * (num_cols - 1))
    
    with cols[0]:
        st.write(f"**{item['id']}** - {item.get('title', 'N/A')}")
    
    with cols[1]:
        if st.button("View", key=f"view_{item['id']}"):
            st.session_state['selected_item'] = item['id']
            st.rerun()
    
    with cols[2]:
        if st.button("Edit", key=f"edit_{item['id']}"):
            st.info("🚧 Edit functionality coming soon")
    
    # Dynamic transition buttons
    for idx, transition in enumerate(available_transitions):
        with cols[3 + idx]:
            button_type = transition.get('button_type', 'secondary')
            if st.button(
                transition['label'],
                key=f"transition_{item['id']}_{transition['to']}",
                type=button_type
            ):
                st.session_state['transition_item'] = item['id']
                st.session_state['transition_config'] = transition
                st.rerun()


def render_items_cards(
    items: list,
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render items as cards."""
    if not items:
        st.info(f"No {doc_type_config['name'].lower()} found matching filters")
        return
    
    for item in items:
        with st.expander(f"▼ {item['id']} - {item.get('title', 'N/A')}", expanded=False):
            # Status
            current_state = item.get('status', workflow_engine.get_initial_state())
            state_info = workflow_engine.get_state_info(current_state)
            st.markdown(f"{state_info['icon']} **Status:** {state_info['label']}")
            
            # Content
            st.markdown(f"**Content:** {item.get('content', 'N/A')}")
            
            # Links
            if item.get('links'):
                st.markdown(f"**Links:** {', '.join(item['links'])}")
            
            # Actions
            render_item_actions(item, doc_type_config, core, workflow_engine)


def render_reports_tab(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore
) -> None:
    """Render reports tab."""
    st.header(f"{doc_type_config['name']} Reports")
    
    prefix = doc_type_config['prefix']
    all_items = core.get_all_items()
    type_items = [
        item for item in all_items
        if item['id'].startswith(prefix.rstrip('-'))
    ]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(type_items))
    with col2:
        approved = len([i for i in type_items if i.get('status') == 'approved'])
        st.metric("Approved", approved)
    with col3:
        verified = len([i for i in type_items if i.get('verification_status') == 'verified'])
        st.metric("Verified", verified)

