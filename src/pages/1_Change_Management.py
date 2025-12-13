"""Change Management page for CompliantFlow."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceability.compliant_flow_core import CompliantFlowCore

st.set_page_config(layout="wide", page_title="Change Management - CompliantFlow")

# Initialize Core
@st.cache_resource
def get_core():
    dhf_root = Path(__file__).resolve().parent.parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)

try:
    core = get_core()
except Exception as e:
    st.error(f"Failed to initialize CompliantFlow Core: {e}")
    st.stop()

# Page Header
st.title("🔄 Change Management")
st.markdown("Track and manage changes to medical device software per IEC 62304 and MDCG 2020-3")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Submit Change", "👀 Review Changes", "📊 Change History"])

# Tab 1: Submit Change Request
with tab1:
    st.header("Submit New Change Request")
    
    with st.form("change_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "Title*",
                placeholder="Brief description of the change",
                help="Short, descriptive title for the change request"
            )
            
            change_type = st.selectbox(
                "Type*",
                options=["bug_fix", "enhancement", "new_feature", "documentation"],
                format_func=lambda x: x.replace('_', ' ').title(),
                help="Type of change being requested"
            )
            
            priority = st.selectbox(
                "Priority*",
                options=["low", "medium", "high", "critical"],
                index=1,  # Default to medium
                format_func=lambda x: x.title(),
                help="Priority level of this change"
            )
        
        with col2:
            created_by = st.text_input(
                "Your Name*",
                placeholder="John Doe",
                help="Person submitting this change request"
            )
            
            # Get all items for multiselect
            all_items = core.get_all_items()
            item_options = [item['id'] for item in all_items]
            
            affected_items = st.multiselect(
                "Affected Items",
                options=item_options,
                help="Select items (requirements, tests, etc.) affected by this change"
            )
        
        description = st.text_area(
            "Description*",
            placeholder="Detailed description of the change...",
            height=150,
            help="Provide a detailed explanation of what needs to change and why"
        )
        
        risk_assessment = st.text_area(
            "Risk Assessment",
            placeholder="Describe any risks introduced by this change...",
            height=100,
            help="Optional: Assess risks introduced by this change"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit_button = st.form_submit_button("Submit Change Request", type="primary")
        with col2:
            clear_button = st.form_submit_button("Clear Form")
    
    if submit_button:
        # Validate required fields
        if not title or not created_by or not description:
            st.error("Please fill in all required fields (marked with *)")
        else:
            try:
                # Create change request
                data = {
                    'title': title,
                    'description': description,
                    'type': change_type,
                    'priority': priority,
                    'created_by': created_by,
                    'affected_items': affected_items,
                    'risk_assessment': risk_assessment if risk_assessment else None
                }
                
                result = core.create_change_request(data, author=created_by)
                
                st.success(f"✅ Change request {result['id']} created successfully!")
                
                # Show impact analysis
                with st.expander("📊 Impact Analysis", expanded=True):
                    impact = core.analyze_change_impact(result['id'])
                    if impact:
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Affected Requirements", len(impact['affected_requirements']))
                        col2.metric("Affected Tests", len(impact['affected_tests']))
                        col3.metric("Affected Risks", len(impact['affected_risks']))
                        col4.metric("Downstream Items", impact['downstream_count'])
                        
                        if impact['is_significant']:
                            st.warning(f"⚠️ **Significant Change**: {impact['significance_rationale']}")
                        else:
                            st.info("ℹ️ This is not considered a significant change per MDCG 2020-3")
                        
                        if impact['impact_summary']:
                            st.text(impact['impact_summary'])
                
                # Suggest next action
                st.info("💡 Next step: Go to 'Review Changes' tab to submit this change for review")
                
            except Exception as e:
                st.error(f"Error creating change request: {e}")

# Tab 2: Review Changes
with tab2:
    st.header("Review Change Requests")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "submitted", "under_review", "approved", "rejected", "implemented", "cancelled"],
            format_func=lambda x: x.replace('_', ' ').title() if x != "All" else "All"
        )
    with col2:
        type_filter = st.selectbox(
            "Filter by Type",
            options=["All", "bug_fix", "enhancement", "new_feature", "documentation"],
            format_func=lambda x: x.replace('_', ' ').title() if x != "All" else "All"
        )
    with col3:
        priority_filter = st.selectbox(
            "Filter by Priority",
            options=["All", "low", "medium", "high", "critical"],
            format_func=lambda x: x.title() if x != "All" else "All"
        )
    
    # Get change requests
    try:
        if status_filter == "All":
            changes = core.list_change_requests()
        else:
            changes = core.list_change_requests(status=status_filter)
        
        # Apply additional filters
        if type_filter != "All":
            changes = [c for c in changes if c['type'] == type_filter]
        if priority_filter != "All":
            changes = [c for c in changes if c['priority'] == priority_filter]
        
        if not changes:
            st.info("No change requests found matching the filters")
        else:
            st.write(f"Found {len(changes)} change request(s)")
            
            # Display each change request
            for change in changes:
                with st.expander(
                    f"{change['id']}: {change['title']} "
                    f"[{change['status'].replace('_', ' ').title()}] "
                    f"[{change['priority'].title()}]",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Type:** {change['type'].replace('_', ' ').title()}")
                        st.write(f"**Created by:** {change['created_by']}")
                        st.write(f"**Created:** {change['created_date'][:19] if isinstance(change['created_date'], str) else change['created_date']}")
                        if change.get('reviewed_by'):
                            st.write(f"**Reviewed by:** {change['reviewed_by']}")
                            st.write(f"**Review date:** {change['review_date'][:19] if isinstance(change['review_date'], str) else change['review_date']}")
                    
                    with col2:
                        st.write(f"**Affected Items:** {len(change['affected_items'])}")
                        if change['affected_items']:
                            st.write(", ".join(change['affected_items'][:5]))
                            if len(change['affected_items']) > 5:
                                st.write(f"... and {len(change['affected_items']) - 5} more")
                    
                    st.write("**Description:**")
                    st.write(change['description'])
                    
                    if change.get('risk_assessment'):
                        st.write("**Risk Assessment:**")
                        st.write(change['risk_assessment'])
                    
                    if change.get('review_comments'):
                        st.write("**Review Comments:**")
                        st.info(change['review_comments'])
                    
                    # Impact Analysis button
                    if st.button(f"📊 Analyze Impact", key=f"impact_{change['id']}"):
                        impact = core.analyze_change_impact(change['id'])
                        if impact:
                            st.write("**Impact Analysis:**")
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Requirements", len(impact['affected_requirements']))
                            col2.metric("Tests", len(impact['affected_tests']))
                            col3.metric("Risks", len(impact['affected_risks']))
                            
                            if impact['is_significant']:
                                st.warning(f"⚠️ Significant: {impact['significance_rationale']}")
                            
                            if impact['impact_summary']:
                                st.code(impact['impact_summary'], language=None)
                    
                    # Workflow actions
                    st.write("---")
                    st.write("**Actions:**")
                    
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if change['status'] == 'submitted':
                            if st.button(f"▶️ Submit for Review", key=f"review_{change['id']}"):
                                from traceability.change_management.workflow import ChangeWorkflow
                                success, msg = ChangeWorkflow.submit_for_review(core.change_tracker, change['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    
                    with action_col2:
                        if change['status'] == 'under_review':
                            reviewer_name = st.text_input(
                                "Reviewer Name",
                                key=f"reviewer_{change['id']}",
                                placeholder="Your name"
                            )
                            comments = st.text_area(
                                "Comments",
                                key=f"comments_{change['id']}",
                                placeholder="Review comments..."
                            )
                            
                            col_approve, col_reject = st.columns(2)
                            with col_approve:
                                if st.button(f"✅ Approve", key=f"approve_{change['id']}", type="primary"):
                                    if not reviewer_name:
                                        st.error("Please enter reviewer name")
                                    else:
                                        result = core.approve_change(change['id'], reviewer_name, comments)
                                        if result['success']:
                                            st.success(result['message'])
                                            st.rerun()
                                        else:
                                            st.error(result['message'])
                            
                            with col_reject:
                                if st.button(f"❌ Reject", key=f"reject_{change['id']}"):
                                    if not reviewer_name or not comments:
                                        st.error("Please enter reviewer name and rejection reason")
                                    else:
                                        result = core.reject_change(change['id'], reviewer_name, comments)
                                        if result['success']:
                                            st.warning(result['message'])
                                            st.rerun()
                                        else:
                                            st.error(result['message'])
                    
                    with action_col3:
                        if change['status'] == 'approved':
                            if st.button(f"✔️ Mark Implemented", key=f"impl_{change['id']}"):
                                from traceability.change_management.workflow import ChangeWorkflow
                                success, msg = ChangeWorkflow.mark_implemented(core.change_tracker, change['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
    
    except Exception as e:
        st.error(f"Error loading change requests: {e}")

# Tab 3: Change History
with tab3:
    st.header("Change Request History")
    
    try:
        all_changes = core.list_change_requests()
        
        if not all_changes:
            st.info("No change requests found")
        else:
            # Create DataFrame for display
            df_data = []
            for change in all_changes:
                df_data.append({
                    'ID': change['id'],
                    'Title': change['title'],
                    'Type': change['type'].replace('_', ' ').title(),
                    'Priority': change['priority'].title(),
                    'Status': change['status'].replace('_', ' ').title(),
                    'Created By': change['created_by'],
                    'Created Date': change['created_date'][:10] if isinstance(change['created_date'], str) else str(change['created_date'])[:10],
                    'Reviewed By': change.get('reviewed_by', ''),
                    'Affected Items': len(change['affected_items'])
                })
            
            df = pd.DataFrame(df_data)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Changes", len(all_changes))
            col2.metric("Pending Review", len([c for c in all_changes if c['status'] in ['submitted', 'under_review']]))
            col3.metric("Approved", len([c for c in all_changes if c['status'] == 'approved']))
            col4.metric("Implemented", len([c for c in all_changes if c['status'] == 'implemented']))
            
            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                }
            )
            
            # Export button
            if st.button("📥 Export to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"change_requests_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error loading change history: {e}")

# Sidebar info
st.sidebar.title("Change Management")
st.sidebar.info(
    """
    **IEC 62304 Compliance**
    
    This module implements change management per:
    - IEC 62304 §6.2 (Change Control)
    - MDCG 2020-3 (Significant Changes)
    
    **Workflow:**
    1. Submit change request
    2. Analyze impact
    3. Review and approve/reject
    4. Implement change
    5. Track in history
    """
)
