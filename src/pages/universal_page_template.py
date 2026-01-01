"""Universal item management page template - works for all item types via configuration."""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from traceability.compliant_flow_core import CompliantFlowCore
from traceability.workflow_engine import DynamicWorkflowEngine
from pages.ui_components import (
    render_manual_verification,
    render_status_badge
)
from utils.ui_helpers import make_item_columns_clickable


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
    
    # Check for item query parameter and auto-select
    item_from_query = None
    if "item" in st.query_params:
        item_from_query = st.query_params["item"]
        # Clear the query param so it doesn't persist
        del st.query_params["item"]
    
    # Clear selection state when switching to a different page
    current_page_key = f"page_{code}"
    if 'current_page_key' not in st.session_state or st.session_state['current_page_key'] != current_page_key:
        # Page changed - clear all selection and editing states
        st.session_state['current_page_key'] = current_page_key
        st.session_state.pop('selected_item_id', None)
        st.session_state.pop('editing_item_id', None)
        st.session_state.pop('creating_new', None)
        st.session_state.pop('transition_item', None)
        st.session_state.pop('transition_config', None)
    
    # Set selected item from query param AFTER clearing page state
    if item_from_query:
        st.session_state['selected_item_id'] = item_from_query
    
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
    # Get metrics from backend
    doc_type_code = doc_type_config.get('code')
    metrics = core.get_doc_type_metrics(doc_type_code)
    
    # Get lifecycle states from config
    lifecycle = doc_type_config.get('lifecycle', {})
    states = lifecycle.get('states', [])
    
    if not states:
        raise ValueError(f"No lifecycle states defined for {doc_type_config.get('name', 'document type')}")
    
    # Show up to 4 state metrics
    num_cols = min(len(states) + 1, 5)  # +1 for Total
    cols = st.columns(num_cols)
    
    with cols[0]:
        st.metric("Total", metrics['total'])
    
    # Show metrics for each state (up to 4)
    for idx, state in enumerate(states[:4]):
        state_id = state['id']
        state_label = state.get('label', state_id.capitalize())
        count = metrics['by_status'].get(state_id, 0)
        with cols[idx + 1]:
            st.metric(state_label, count)



def render_table_section(
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine,
    prefix: str
) -> None:
    """Render table section with New button and filters."""
    # Header with Items title and New button only
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("Items")
    with col2:
        if st.button("➕ New", type="primary", use_container_width=True):
            st.session_state['creating_new'] = True
            st.session_state['selected_item_id'] = None
            st.rerun()
    
    # Document Preview Section - Always visible
    with st.expander("📄 Preview Specification", expanded=False):
        st.markdown("**Document Operations**")
        
        # Buttons for document operations
        col_regen, col_export = st.columns(2)
        
        with col_regen:
            if st.button("🔄 Regenerate Document", use_container_width=True, help="Update static markdown file from current YAML items", key="regen_btn"):
                # Generate markdown and save to static file
                try:
                    from pathlib import Path
                    from traceability.document_generator import DocumentGenerator
                    
                    # Show progress
                    with st.spinner("Regenerating document..."):
                        template_dir = Path(core.repo_root).parent / "DHF" / "documents" / "specifications" / "templates"
                        generator = DocumentGenerator(core, template_dir)
                        
                        doc_type_code = doc_type_config['code']
                        markdown_content, output_path = generator.generate_markdown_spec(doc_type_code)
                        
                        # Extract version from generated content
                        import re
                        version_match = re.search(r'\*\*Version\*\*:\s*(\d+\.\d+)', markdown_content)
                        version = version_match.group(1) if version_match else "Unknown"
                        
                        # Store in session state for display - scoped to doc type
                        st.session_state[f'preview_content_{doc_type_code}'] = markdown_content
                        st.session_state[f'last_regeneration_{doc_type_code}'] = {
                            'success': True,
                            'filename': output_path.name,
                            'path': str(output_path),
                            'version': version
                        }
                    
                    # Show toast notification that persists
                    st.toast(f"✅ Successfully regenerated {output_path.name} (v{version})", icon="✅")
                    st.rerun()
                        
                except Exception as e:
                    doc_type_code = doc_type_config['code']
                    st.session_state[f'last_regeneration_{doc_type_code}'] = {
                        'success': False,
                        'error': str(e)
                    }
                    st.toast(f"❌ Error regenerating document", icon="❌")
                    st.error(f"Error regenerating document: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Show status message from last regeneration - scoped to doc type
        doc_type_code = doc_type_config['code']
        if f'last_regeneration_{doc_type_code}' in st.session_state:
            regen_info = st.session_state[f'last_regeneration_{doc_type_code}']
            if regen_info['success']:
                version_info = f" (v{regen_info.get('version', 'Unknown')})" if 'version' in regen_info else ""
                st.success(f"✅ Last regenerated: {regen_info['filename']}{version_info} - Status: Draft")
                st.info(f"📝 File: `{regen_info['path']}`\n\nReview with `git diff` and commit the changes.")
            else:
                st.error(f"❌ Last regeneration failed: {regen_info['error']}")
        
        with col_export:
            # Export static file to PDF - one-click download
            try:
                from pathlib import Path
                from traceability.document_generator import DocumentGenerator
                
                template_dir = Path(core.repo_root).parent / "DHF" / "documents" / "specifications" / "templates"
                generator = DocumentGenerator(core, template_dir)
                
                doc_type_code = doc_type_config['code']
                
                # Check if static file exists first
                import yaml
                config_path = core.repo_root / 'config' / 'project_config.yaml'
                with open(config_path, 'r') as f:
                    project_config = yaml.safe_load(f)
                
                doc_specs = project_config.get('document_specifications', {})
                if doc_type_code in doc_specs:
                    spec_config = doc_specs[doc_type_code]
                    static_file_path = core.repo_root.parent / spec_config['output']
                    
                    if static_file_path.exists():
                        # Generate PDF and provide immediate download
                        pdf_path = generator.export_static_doc_to_pdf(doc_type_code)
                        
                        with open(pdf_path, 'rb') as f:
                            st.download_button(
                                label="📄 Export PDF",
                                data=f.read(),
                                file_name=f"{doc_type_code}_Specification.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                key="export_pdf_btn",
                                help="Download specification as PDF"
                            )
                    else:
                        st.button(
                            "📄 Export PDF",
                            use_container_width=True,
                            disabled=True,
                            help="Static document not found. Regenerate first.",
                            key="export_pdf_disabled"
                        )
                        
            except Exception as e:
                st.button(
                    "📄 Export PDF",
                    use_container_width=True,
                    disabled=True,
                    help=f"Error: {str(e)}",
                    key="export_pdf_error"
                )
        
        st.markdown("---")
        st.markdown("**Document Preview**")
        
        # Load and display the static file - scoped to doc type
        try:
            import yaml
            config_path = core.repo_root / 'config' / 'project_config.yaml'
            with open(config_path, 'r') as f:
                project_config = yaml.safe_load(f)
            
            doc_specs = project_config.get('document_specifications', {})
            doc_type_code = doc_type_config['code']
            
            if doc_type_code in doc_specs:
                spec_config = doc_specs[doc_type_code]
                static_file_path = core.repo_root.parent / spec_config['output']
                
                if static_file_path.exists():
                    # Load from file if not in session state for this doc type
                    preview_key = f'preview_content_{doc_type_code}'
                    if preview_key not in st.session_state:
                        st.session_state[preview_key] = static_file_path.read_text()
                    
                    # Display the preview
                    st.markdown(st.session_state[preview_key], unsafe_allow_html=True)
                else:
                    st.warning(f"📝 Static document not found: `{static_file_path.name}`")
                    st.info("Click '🔄 Regenerate Document' to create the specification file.")
            else:
                st.info(f"No document specification configured for {doc_type_code}")
                
        except Exception as e:
            st.error(f"Error loading preview: {str(e)}")
    
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
        # Use exact prefix match (don't strip hyphen)
        if not item['id'].startswith(prefix):
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
        # Create simple table with ID, Title, Status only
        df_data = []
        for item in filtered_items:
            df_data.append({
                'ID': item['id'],
                'Title': item.get('title', 'N/A'),
                'Status': item.get('status', workflow_engine.get_initial_state())
            })
        
        df = pd.DataFrame(df_data)
        
        # Configure clickable item ID columns (for ID column and all relationship columns)
        df, column_config = make_item_columns_clickable(df, core)
        
        # Use dataframe with on_click selection (no checkboxes)
        event = st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="items_table",
            column_config=column_config
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
    
    # Check if transitioning
    if st.session_state.get('transition_item') and st.session_state.get('transition_to_state'):
        item_id = st.session_state['transition_item']
        to_state = st.session_state['transition_to_state']
        item = core.get_item(item_id)
        if item:
            render_transition_workflow(item, to_state, doc_type_config, core)
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
    
    # Initialize form data
    form_data = {}
    
    # Display info that ID will be auto-generated
    st.info("ℹ️ **ID will be auto-generated** when you create this item")
    
    # Get form schema from backend (without item_id for create mode)
    doc_type_code = doc_type_config.get('code')
    schema = core.get_form_schema(doc_type_code, item_id=None)
    
    # Render fields based on schema
    for field in schema['fields']:
        field_name = field['name']
        label = field['label'] + (' *' if field.get('required') else '')
        field_type = field.get('type', 'text')
        placeholder = field.get('placeholder')
        help_text = field.get('help')
        
        if field_type == 'text':
            form_data[field_name] = st.text_input(label, placeholder=placeholder or '', 
                                                   help=help_text, key=f"new_{field_name}")
        elif field_type == 'textarea':
            height = field.get('height', 100)
            form_data[field_name] = st.text_area(label, height=height, placeholder=placeholder or '',
                                                  help=help_text, key=f"new_{field_name}")
        elif field_type == 'markdown':
            height = field.get('height', 150)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Editor**")
                form_data[field_name] = st.text_area(label, height=height, placeholder=placeholder or '',
                                                      help=help_text, key=f"new_{field_name}")
            with col2:
                st.write("**Preview**")
                st.markdown(form_data.get(field_name, ''))
        elif field_type == 'url':
            form_data[field_name] = st.text_input(label, placeholder=placeholder or 'https://',
                                                   help=help_text, key=f"new_{field_name}")
        elif field_type == 'select':
            options = field.get('options', [])
            default_idx = 0
            if field.get('current_value') and field['current_value'] in options:
                default_idx = options.index(field['current_value'])
            form_data[field_name] = st.selectbox(label, options, index=default_idx,
                                                  help=help_text, key=f"new_{field_name}")
        elif field_type == 'multiselect':
            options = field.get('options', [])
            default = field.get('current_value', [])
            if isinstance(default, str):
                default = [default] if default else []
            form_data[field_name] = st.multiselect(label, options, default=default,
                                                    help=help_text, key=f"new_{field_name}")
        elif field_type == 'radio':
            options = field.get('options', [])
            form_data[field_name] = st.radio(label, options, help=help_text, key=f"new_{field_name}")
        elif field_type == 'checkbox':
            default = field.get('current_value', False)
            form_data[field_name] = st.checkbox(label, value=default, help=help_text, key=f"new_{field_name}")
        elif field_type == 'toggle':
            default = field.get('current_value', False)
            form_data[field_name] = st.toggle(label, value=default, help=help_text, key=f"new_{field_name}")
        elif field_type == 'number':
            min_val = field.get('min_value')
            max_val = field.get('max_value')
            form_data[field_name] = st.number_input(label, min_value=min_val, max_value=max_val,
                                                     help=help_text, key=f"new_{field_name}")
        elif field_type == 'slider':
            min_val = field.get('min_value', 0)
            max_val = field.get('max_value', 100)
            step = field.get('step', 1)
            form_data[field_name] = st.slider(label, min_value=min_val, max_value=max_val, step=step,
                                               help=help_text, key=f"new_{field_name}")
        elif field_type == 'date':
            form_data[field_name] = st.date_input(label, help=help_text, key=f"new_{field_name}")
        elif field_type == 'datetime':
            col1, col2 = st.columns(2)
            with col1:
                date_val = st.date_input(f"{label} (Date)", help=help_text, key=f"new_{field_name}_date")
            with col2:
                time_val = st.time_input(f"{label} (Time)", key=f"new_{field_name}_time")
            form_data[field_name] = f"{date_val} {time_val}"
        elif field_type in ['item_reference', 'item_multiselect', 'relationship']:
            options = field.get('options', [])
            if field_type == 'item_reference':
                form_data[field_name] = st.selectbox(label, options, help=help_text, key=f"new_{field_name}")
            else:
                default = field.get('current_value', [])
                if isinstance(default, str):
                    default = [default] if default else []
                form_data[field_name] = st.multiselect(label, options, default=default,
                                                        help=help_text, key=f"new_{field_name}")
        elif field_type == 'file_upload':
            allowed_types = field.get('allowed_extensions')
            form_data[field_name] = st.file_uploader(label, type=allowed_types, help=help_text,
                                                      key=f"new_{field_name}")

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Create", type="primary", use_container_width=True, key="create_btn"):
            # Validate required fields
            # Validate required fields dynamically
            missing_fields = []
            # ID is auto-generated, so we don't require it in validation
                
            for field in schema['fields']:
                if field.get('required') and not form_data.get(field['name']):
                    # Checkbox/Select might be False/0 but valid?
                    # For now assume text fields.
                    if field.get('type') == 'checkbox': continue
                    missing_fields.append(field['label'].replace(' *', ''))
            
            if missing_fields:
                for missing in missing_fields:
                    st.error(f"{missing} is required")
            else:
                # Create new item with all filled fields
                new_item = {
                    'type': doc_type_config['code'],  # Required for ID auto-generation
                    # Note: status is auto-set by backend based on lifecycle config
                }
                
                # Add ID if manually provided (though it shouldn't be for this flow)
                if form_data.get('id'):
                    new_item['id'] = form_data['id']
                
                # Add all other fields that have values
                for key, value in form_data.items():
                    if key != 'id' and value:  # Skip empty values
                        new_item[key] = value
                
                # Save item using create_item (not update_item)
                try:
                    created_item = core.create_item(new_item)
                    st.success(f"✅ Created {created_item['id']}")
                    
                    # Clear creation mode and select new item
                    st.session_state['creating_new'] = False
                    st.session_state['selected_item_id'] = created_item['id']
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
    # CR Confirmation Dialog
    if 'confirm_add_to_cr' in st.session_state:
        confirm_data = st.session_state['confirm_add_to_cr']
        
        st.warning(f"⚠️ **Confirm Action**")
        st.write(f"Add **{confirm_data['item_id']}** to Change Request **{confirm_data['cr_id']}**?")
        st.caption(f"CR Title: {confirm_data['cr_title']}")
        st.caption(f"CR Status: {confirm_data['cr_status']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm", type="primary", use_container_width=True, key="confirm_add_cr"):
                from utils.cr_manager import add_item_to_cr
                if add_item_to_cr(confirm_data['cr_id'], confirm_data['item_id'], core):
                    st.success(f"✅ Added {confirm_data['item_id']} to {confirm_data['cr_id']}")
                    st.session_state['editing_item_id'] = confirm_data['item_id']
                    st.session_state['active_cr_id'] = confirm_data['cr_id']
                    del st.session_state['confirm_add_to_cr']
                    st.rerun()
                else:
                    st.error(f"Failed to add item to CR (CR may be in stable status)")
                    del st.session_state['confirm_add_to_cr']
        with col2:
            if st.button("❌ Cancel", use_container_width=True, key="cancel_add_cr"):
                del st.session_state['confirm_add_to_cr']
                st.rerun()
        
        st.markdown("---")
    
    # Header with Edit button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{item['id']} - {item.get('title', 'N/A')}")
    with col2:
        # Check if item can be edited (backend handles all CR logic)
        can_edit, button_label, cr_id, available_cr = core.can_edit_item(item['id'])
        
        if can_edit:
            if st.button(button_label, use_container_width=True, key=f"edit_{item['id']}"):
                st.session_state['editing_item_id'] = item['id']
                if cr_id:
                    st.session_state['active_cr_id'] = cr_id
                st.rerun()
        elif available_cr:
            # Show "Add to CR" button
            if st.button(button_label, use_container_width=True, key=f"add_to_cr_{item['id']}"):
                st.session_state['confirm_add_to_cr'] = {
                    'item_id': item['id'],
                    'cr_id': available_cr['id'],
                    'cr_title': available_cr.get('title', ''),
                    'cr_status': available_cr.get('status', '')
                }
                st.rerun()
        else:
            # Locked - no CR available
            st.button(
                button_label,
                use_container_width=True,
                key=f"edit_{item['id']}",
                disabled=True,
                help="Cannot edit items with stable status. Create/approve a CR to modify."
            )
    
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
    
    # Show CR info if change control is enabled and item is stable
    if state_info.get('is_stable', False):
        from utils.cr_manager import is_change_control_enabled, get_cr_for_item, get_cr_doc_type
        if is_change_control_enabled(core):
            linked_cr = get_cr_for_item(item['id'], core)
            if linked_cr:
                cr_type = get_cr_doc_type(core)
                cr_status = linked_cr.get('status', '')
                st.info(f"📝 Linked {cr_type}: [{linked_cr['id']}] {linked_cr.get('title', '')} (Status: {cr_status})")
    
    # Get properties from config to show all fields
    properties = doc_type_config.get('properties', [])
    
    # Fields to skip (system/internal fields)
    skip_fields = {'id', 'status', 'approved_by', 'approved_date', 'retired_by', 
                   'retired_date', 'manual_verifications', 'history', 'links',
                   'active', 'reviewer', 'review_date', 'verified_by', 'verified_date'}
    
    # Display all configured fields
    for prop in properties:
        # Handle new dictionary format for properties
        prop_name = prop
        display_label = None
        
        if isinstance(prop, dict):
            # STRICT: Property config must be a dict with 'name' (validated by core/process)
            # We assume config is valid or at least try to get 'name'
            if 'name' in prop:
                prop_name = prop['name']
                display_label = prop.get('label')
            else:
                st.error(f"Invalid property config in UI: {prop}")
                continue
        
        if prop_name in skip_fields:
            continue
            
        # Get value from item
        value = item.get(prop_name)
        
        # Determine display label
        if display_label:
            field_name = display_label
        else:
            field_name = prop_name.replace('_', ' ').title()
        
        # Smart rendering for list fields containing item IDs
        if isinstance(value, list) and value:
            # Check if this looks like a list of item IDs (e.g., "SYS-001", "RISK-042")
            # Item IDs typically have format: LETTERS-NUMBERS
            first_item = value[0] if value else None
            is_item_list = False
            
            if isinstance(first_item, str):
                # Check if it matches item ID pattern (e.g., SYS-001, RISK-042)
                import re
                if re.match(r'^[A-Z]+-\d+', first_item):
                    is_item_list = True
            
            if is_item_list:
                # Import URL helper
                from utils.ui_helpers import get_page_url_for_item
                
                # Render as clickable links with item details
                st.markdown(f"**{field_name}:**")
                for item_id in value:
                    linked_item = core.get_item(item_id)
                    if linked_item:
                        item_title = linked_item.get('title', 'N/A')
                        item_status = linked_item.get('status', 'unknown')
                        # Create clickable link using consistent URL helper
                        item_url = get_page_url_for_item(item_id, core)
                        st.markdown(f"  - [{item_id}]({item_url}): {item_title} _({item_status})_")
                    else:
                        st.markdown(f"  - {item_id} _(not found)_")
                continue
        
        # Special handling for implementation_prs (list of dicts)
        if prop == 'implementation_prs' and isinstance(value, list):
            st.markdown(f"**{field_name}:**")
            if value:
                for pr in value:
                    if isinstance(pr, dict):
                        pr_num = pr.get('pr_number', 'N/A')
                        pr_url = pr.get('pr_url', '')
                        pr_title = pr.get('title', 'No title')
                        # Format PR link nicely
                        if pr_url:
                            st.markdown(f"  - [PR #{pr_num}]({pr_url}): {pr_title}")
                        else:
                            st.markdown(f"  - PR #{pr_num}: {pr_title}")
                    else:
                        st.markdown(f"  - {pr}")
            else:
                st.caption("  _(empty)_")
            continue
        
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
                st.text_area(field_name, value, height=100, disabled=True, key=f"field_{prop_name}_{item['id']}", label_visibility="collapsed")
            else:
                st.markdown(f"**{field_name}:** `{value}`")


    # Workflow transition buttons
    st.markdown("---")
    st.markdown("### Workflow Actions")
    
    # Use new lifecycle methods from core
    available_transitions = core.get_available_transitions(item)
    
    if available_transitions:
        cols = st.columns(len(available_transitions))
        for idx, transition in enumerate(available_transitions):
            with cols[idx]:
                if st.button(
                    transition.get('action_label', transition.get('label', 'Transition')),
                    key=f"transition_{item['id']}_{transition.get('to_state', transition.get('to'))}",
                    use_container_width=True,
                    type="primary" if idx == 0 else "secondary"
                ):
                    st.session_state['transition_item'] = item['id']
                    st.session_state['transition_to_state'] = transition.get('to_state', transition.get('to'))
                    st.rerun()
    else:
        st.info(f"No transitions available from {state_info['label']} state")
    
    # Git History Section (collapsible, similar to preview)
    st.markdown("---")
    
    if item.get('file_path'):
        from utils.git_history import get_full_commit_history
        from pathlib import Path
        
        with st.expander("📜 Change History", expanded=False):
            try:
                item_path = Path(item['file_path'])
                dhf_root = core.repo_root
                commits = get_full_commit_history(item_path, dhf_root)
                
                if commits:
                    for commit in commits:
                        # Create a summary line for each commit
                        commit_date = commit['timestamp'][:19]
                        commit_hash = commit['commit_hash'][:7]
                        author = commit['author_name']
                        message = commit['message']
                        num_changes = len(commit.get('changes', []))
                        
                        # Create an expander for each commit
                        summary = f"**{commit_date}** | {commit_hash} | {author} | {message[:50]}{'...' if len(message) > 50 else ''}"
                        if num_changes > 0:
                            summary += f" ({num_changes} field{'s' if num_changes != 1 else ''} changed)"
                        
                        with st.expander(summary, expanded=False):
                            if commit.get('changes'):
                                # Show changes as a table
                                import pandas as pd
                                changes_data = []
                                for change in commit['changes']:
                                    changes_data.append({
                                        'Field': change['field'],
                                        'Before': change['old_value'] if change['old_value'] is not None else '(new)',
                                        'After': change['new_value']
                                    })
                                
                                df = pd.DataFrame(changes_data)
                                st.dataframe(df, width="stretch", hide_index=True)
                            else:
                                st.caption("No field changes detected (possibly file creation or non-YAML changes)")
                            
                            # Show full commit details
                            st.caption(f"**Full message:** {message}")
                            st.caption(f"**Commit:** {commit['commit_hash']}")
                            st.caption(f"**Author:** {author} ({commit['author_email']})")
                else:
                    st.info("No commit history found in git.")
            except Exception as e:
                st.warning(f"Could not load git history: {str(e)}")
    else:
        with st.expander("📜 Change History", expanded=False):
            st.info("Git history not available for this item.")



def render_item_edit_form(
    item: Dict[str, Any],
    doc_type_config: Dict[str, Any],
    core: CompliantFlowCore,
    workflow_engine: DynamicWorkflowEngine
) -> None:
    """Render editable form for item."""
    st.subheader(f"✏️ Edit {item['id']}")
    
    # Note: Edit permission is already validated by can_edit_item() in the backend
    # If user reached this form, they have permission to edit
    
    # Get form schema from backend
    doc_type_code = doc_type_config.get('code')
    schema = core.get_form_schema(doc_type_code, item['id'])
    
    # Form fields - dynamically
    form_data = {}
    
    st.divider()
    
    # Render fields based on schema (skip ID field)
    for field in schema['fields']:
        field_name = field['name']
        
        # Skip ID field - already displayed as read-only above
        if field_name == 'id':
            continue
        
        label = field['label'] + (' *' if field.get('required') else '')
        current_value = field.get('current_value', '')
        field_type = field.get('type', 'text')
        placeholder = field.get('placeholder')
        help_text = field.get('help')
        
        if field_type == 'text':
            form_data[field_name] = st.text_input(label, value=current_value if current_value else '', 
                                                   placeholder=placeholder or '', help=help_text,
                                                   key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'textarea':
            height = field.get('height', 100)
            form_data[field_name] = st.text_area(label, value=current_value if current_value else '', 
                                                 height=height, placeholder=placeholder or '', help=help_text,
                                                 key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'markdown':
            height = field.get('height', 150)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Editor**")
                form_data[field_name] = st.text_area(label, value=current_value if current_value else '',
                                                      height=height, placeholder=placeholder or '', help=help_text,
                                                      key=f"edit_{field_name}_{item['id']}")
            with col2:
                st.write("**Preview**")
                st.markdown(form_data.get(field_name, current_value or ''))
        elif field_type == 'url':
            form_data[field_name] = st.text_input(label, value=current_value if current_value else '',
                                                   placeholder=placeholder or 'https://', help=help_text,
                                                   key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'select':
            options = field.get('options', [])
            default_idx = options.index(current_value) if current_value in options else 0
            form_data[field_name] = st.selectbox(label, options, index=default_idx, help=help_text,
                                                 key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'multiselect' or field_type in ['item_multiselect', 'relationship']:
            options = field.get('options', [])
            # Ensure "default" is a list
            default = current_value if isinstance(current_value, list) else ([current_value] if current_value else [])
            
            # CRITICAL FIX: Ensure all default values are in options to prevent Streamlit crash
            # This handles stale references or items not returned by get_all_items
            for val in default:
                if val not in options:
                    options.append(val)
            
            form_data[field_name] = st.multiselect(label, options, default=default, help=help_text,
                                                    key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'radio':
            options = field.get('options', [])
            default_idx = options.index(current_value) if current_value in options else 0
            form_data[field_name] = st.radio(label, options, index=default_idx, help=help_text,
                                              key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'checkbox':
            form_data[field_name] = st.checkbox(label, value=bool(current_value), help=help_text,
                                                 key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'toggle':
            form_data[field_name] = st.toggle(label, value=bool(current_value), help=help_text,
                                               key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'number':
            min_val = field.get('min_value')
            max_val = field.get('max_value')
            val = float(current_value) if current_value else 0.0
            form_data[field_name] = st.number_input(label, value=val, min_value=min_val, max_value=max_val,
                                                     help=help_text, key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'slider':
            min_val = field.get('min_value', 0)
            max_val = field.get('max_value', 100)
            step = field.get('step', 1)
            val = float(current_value) if current_value else min_val
            form_data[field_name] = st.slider(label, min_value=min_val, max_value=max_val, value=val, step=step,
                                               help=help_text, key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'date':
            form_data[field_name] = st.date_input(label, value=current_value if current_value else None,
                                                   help=help_text, key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'datetime':
            col1, col2 = st.columns(2)
            with col1:
                date_val = st.date_input(f"{label} (Date)", help=help_text,
                                          key=f"edit_{field_name}_date_{item['id']}")
            with col2:
                time_val = st.time_input(f"{label} (Time)", key=f"edit_{field_name}_time_{item['id']}")
            form_data[field_name] = f"{date_val} {time_val}"
        elif field_type in ['item_reference', 'item_multiselect', 'relationship']:
            options = field.get('options', [])
            if field_type == 'item_reference':
                default_idx = options.index(current_value) if current_value in options else 0
                form_data[field_name] = st.selectbox(label, options, index=default_idx, help=help_text,
                                                      key=f"edit_{field_name}_{item['id']}")
            else:
                default = current_value if isinstance(current_value, list) else []
                form_data[field_name] = st.multiselect(label, options, default=default, help=help_text,
                                                        key=f"edit_{field_name}_{item['id']}")
        elif field_type == 'file_upload':
            allowed_types = field.get('allowed_extensions')
            form_data[field_name] = st.file_uploader(label, type=allowed_types, help=help_text,
                                                      key=f"edit_{field_name}_{item['id']}")

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save", type="primary", use_container_width=True, key=f"save_edit_{item['id']}"):
            # Validate required fields
            # Validate required fields dynamically
            missing_fields = []
            for field in schema['fields']:
                if field.get('required') and not form_data.get(field['name']):
                    if field.get('type') == 'checkbox': continue
                    missing_fields.append(field['label'].replace(' *', ''))
            
            if missing_fields:
                for missing in missing_fields:
                    st.error(f"{missing} is required")
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
                
                # Save item (core will handle status reset if needed)
                try:
                    # Get active CR if editing stable item
                    cr_id = st.session_state.get('active_cr_id')
                    
                    core.update_item(item['id'], updated_item, cr_id=cr_id)
                    st.success(f"✅ Saved {item['id']}")
                    
                    # Clear CR session state
                    if 'active_cr_id' in st.session_state:
                        del st.session_state['active_cr_id']
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
        
        # Collect metadata for transition
        # Use pattern: {to_state}_by and {to_state}_date
        to_state = transition['to']
        by_field = f"{to_state}_by"
        date_field = f"{to_state}_date"
        
        # Show input for who performed the transition
        performed_by = st.text_input(
            f"{transition['label']} by *",
            key=f"transition_by_{item['id']}_{to_state}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ {transition['label']}", type="primary", use_container_width=True, key="confirm_transition"):
                if not performed_by:
                    st.warning("Please enter your name")
                else:
                    # Build metadata with generic pattern
                    metadata = {
                        by_field: performed_by,
                        date_field: datetime.now().date().isoformat(),  # Use date() for date fields
                        'timestamp': datetime.now().isoformat()
                    }
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
    st.dataframe(df, width="stretch", hide_index=True)
    
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
    
    # Get lifecycle states from config
    lifecycle = doc_type_config.get('lifecycle', {})
    states = lifecycle.get('states', [])
    
    if states:
        # Show metrics for first few states
        num_metrics = min(len(states), 3)
        cols = st.columns(num_metrics + 1)  # +1 for Total
        
        with cols[0]:
            st.metric("Total", len(type_items))
        
        for idx, state in enumerate(states[:num_metrics]):
            state_id = state['id']
            state_label = state.get('label', state_id.capitalize())
            count = len([i for i in type_items if i.get('status') == state_id])
            with cols[idx + 1]:
                st.metric(state_label, count)
    else:
        # Fallback
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", len(type_items))
        with col2:
            if doc_type_config.get('has_verification'):
                verified = len([i for i in type_items if i.get('verification_status') == 'PASS'])
                st.metric("Verified", verified)

