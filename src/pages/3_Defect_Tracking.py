"""Defect Tracking page for CompliantFlow."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceability.compliant_flow_core import CompliantFlowCore

st.set_page_config(layout="wide", page_title="Defect Tracking - CompliantFlow")

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
st.title("🐛 Defect Tracking")
st.markdown("Track and manage software defects per IEC 62304 §9.7")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Report Defect", "🔍 Manage Defects", "📊 Defect History"])

# Tab 1: Report Defect
with tab1:
    st.header("Report New Defect")
    
    with st.form("report_defect_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "Title*",
                placeholder="Brief description of the defect",
                help="Short, descriptive title for the defect"
            )
            
            severity = st.selectbox(
                "Severity*",
                options=["critical", "major", "minor", "cosmetic"],
                index=1,  # Default to major
                format_func=lambda x: {
                    "critical": "🔴 Critical - System crash, data loss, safety issue",
                    "major": "🟠 Major - Major functionality broken",
                    "minor": "🟡 Minor - Minor functionality issue",
                    "cosmetic": "🟢 Cosmetic - UI/UX issue, no functional impact"
                }[x],
                help="Severity level of the defect"
            )
            
            reported_by = st.text_input(
                "Your Name*",
                placeholder="John Doe",
                help="Person reporting this defect"
            )
        
        with col2:
            # Get all items for multiselect
            all_items = core.get_all_items()
            item_options = [item['id'] for item in all_items]
            
            affected_items = st.multiselect(
                "Affected Items",
                options=item_options,
                help="Select items (requirements, tests, etc.) affected by this defect"
            )
            
            environment = st.text_input(
                "Environment",
                placeholder="e.g., dev, test, production",
                help="Environment where defect was found"
            )
            
            tags = st.text_input(
                "Tags (comma-separated)",
                placeholder="e.g., ui, performance, security",
                help="Tags for categorization"
            )
        
        description = st.text_area(
            "Description*",
            placeholder="Detailed description of the defect...",
            height=150,
            help="Provide a detailed explanation of the defect"
        )
        
        steps_to_reproduce = st.text_area(
            "Steps to Reproduce",
            placeholder="1. Navigate to...\n2. Click on...\n3. Observe...",
            height=100,
            help="Steps to reproduce the defect"
        )
        
        submit = st.form_submit_button("Report Defect", type="primary")
    
    if submit:
        if not title or not reported_by or not description:
            st.error("Please fill in all required fields (marked with *)")
        else:
            try:
                # Parse tags
                tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
                
                # Create defect
                data = {
                    'title': title,
                    'description': description,
                    'severity': severity,
                    'reported_by': reported_by,
                    'affected_items': affected_items,
                    'environment': environment if environment else None,
                    'steps_to_reproduce': steps_to_reproduce if steps_to_reproduce else None,
                    'tags': tag_list
                }
                
                result = core.create_defect(data, author=reported_by)
                
                st.success(f"✅ Defect {result['id']} reported successfully!")
                st.info(f"💡 Next step: Assign this defect to an investigator in the 'Manage Defects' tab")
                
                # Show defect details
                with st.expander("📋 Defect Details", expanded=True):
                    st.write(f"**ID:** {result['id']}")
                    st.write(f"**Title:** {result['title']}")
                    st.write(f"**Severity:** {result['severity'].upper()}")
                    st.write(f"**Status:** {result['status'].replace('_', ' ').title()}")
                    if result.get('affected_items'):
                        st.write(f"**Affected Items:** {', '.join(result['affected_items'])}")
                
            except Exception as e:
                st.error(f"Error reporting defect: {e}")

# Tab 2: Manage Defects
with tab2:
    st.header("Manage Defects")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "open", "investigating", "resolved", "verified", "closed", "deferred", "reopened"],
            format_func=lambda x: x.replace('_', ' ').title() if x != "All" else "All"
        )
    with col2:
        severity_filter = st.selectbox(
            "Filter by Severity",
            options=["All", "critical", "major", "minor", "cosmetic"],
            format_func=lambda x: x.title() if x != "All" else "All"
        )
    with col3:
        assigned_filter = st.text_input("Filter by Assigned To", placeholder="Enter name")
    
    # Get defects
    try:
        if status_filter == "All":
            defects = core.list_defects(
                severity=severity_filter if severity_filter != "All" else None,
                assigned_to=assigned_filter if assigned_filter else None
            )
        else:
            defects = core.list_defects(
                status=status_filter,
                severity=severity_filter if severity_filter != "All" else None,
                assigned_to=assigned_filter if assigned_filter else None
            )
        
        if not defects:
            st.info("No defects found matching the filters")
        else:
            st.write(f"Found {len(defects)} defect(s)")
            
            # Display each defect
            for defect in defects:
                severity_icon = {
                    "critical": "🔴",
                    "major": "🟠",
                    "minor": "🟡",
                    "cosmetic": "🟢"
                }.get(defect['severity'], "⚪")
                
                with st.expander(
                    f"{severity_icon} {defect['id']}: {defect['title']} "
                    f"[{defect['status'].replace('_', ' ').title()}]",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Severity:** {defect['severity'].upper()}")
                        st.write(f"**Status:** {defect['status'].replace('_', ' ').title()}")
                        st.write(f"**Reported by:** {defect['reported_by']}")
                        st.write(f"**Reported:** {defect['reported_date'][:19] if isinstance(defect['reported_date'], str) else defect['reported_date']}")
                        if defect.get('assigned_to'):
                            st.write(f"**Assigned to:** {defect['assigned_to']}")
                    
                    with col2:
                        if defect.get('environment'):
                            st.write(f"**Environment:** {defect['environment']}")
                        if defect.get('affected_items'):
                            st.write(f"**Affected Items:** {len(defect['affected_items'])}")
                            st.write(", ".join(defect['affected_items'][:3]))
                            if len(defect['affected_items']) > 3:
                                st.write(f"... and {len(defect['affected_items']) - 3} more")
                        if defect.get('tags'):
                            st.write(f"**Tags:** {', '.join(defect['tags'])}")
                    
                    st.write("**Description:**")
                    st.write(defect['description'])
                    
                    if defect.get('steps_to_reproduce'):
                        st.write("**Steps to Reproduce:**")
                        st.code(defect['steps_to_reproduce'], language=None)
                    
                    if defect.get('root_cause'):
                        st.write("**Root Cause:**")
                        st.info(defect['root_cause'])
                    
                    if defect.get('resolution'):
                        st.write("**Resolution:**")
                        st.success(defect['resolution'])
                    
                    if defect.get('verification'):
                        st.write("**Verification:**")
                        st.success(defect['verification'])
                    
                    # Action buttons based on status
                    st.write("---")
                    st.write("**Actions:**")
                    
                    if defect['status'] == 'open':
                        col_assign, col_investigate = st.columns(2)
                        
                        with col_assign:
                            assignee = st.text_input(
                                "Assign to",
                                key=f"assignee_{defect['id']}",
                                placeholder="Name"
                            )
                            if st.button(f"👤 Assign", key=f"assign_{defect['id']}"):
                                if not assignee:
                                    st.error("Please enter assignee name")
                                else:
                                    result = core.assign_defect(defect['id'], assignee, author=assignee)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                        
                        with col_investigate:
                            investigator = st.text_input(
                                "Investigator",
                                key=f"investigator_{defect['id']}",
                                placeholder="Name"
                            )
                            if st.button(f"🔍 Start Investigation", key=f"investigate_{defect['id']}"):
                                if not investigator:
                                    st.error("Please enter investigator name")
                                else:
                                    result = core.start_defect_investigation(defect['id'], author=investigator)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                    
                    elif defect['status'] == 'investigating':
                        root_cause = st.text_area(
                            "Root Cause Analysis",
                            key=f"root_cause_{defect['id']}",
                            placeholder="Describe the root cause..."
                        )
                        resolution = st.text_area(
                            "Resolution",
                            key=f"resolution_{defect['id']}",
                            placeholder="Describe how it was resolved..."
                        )
                        resolver = st.text_input(
                            "Resolver Name",
                            key=f"resolver_{defect['id']}",
                            placeholder="Your name"
                        )
                        
                        if st.button(f"✅ Mark Resolved", key=f"resolve_{defect['id']}", type="primary"):
                            if not root_cause or not resolution or not resolver:
                                st.error("Please fill in all fields")
                            else:
                                result = core.resolve_defect(defect['id'], root_cause, resolution, author=resolver)
                                if result['success']:
                                    st.success(result['message'])
                                    st.rerun()
                                else:
                                    st.error(result['message'])
                    
                    elif defect['status'] == 'resolved':
                        verification = st.text_area(
                            "Verification Details",
                            key=f"verification_{defect['id']}",
                            placeholder="Describe how you verified the fix..."
                        )
                        verifier = st.text_input(
                            "Verifier Name",
                            key=f"verifier_{defect['id']}",
                            placeholder="Your name"
                        )
                        
                        col_verify, col_reopen = st.columns(2)
                        with col_verify:
                            if st.button(f"✔️ Verify Resolution", key=f"verify_{defect['id']}", type="primary"):
                                if not verification or not verifier:
                                    st.error("Please fill in all fields")
                                else:
                                    result = core.verify_defect_resolution(defect['id'], verification, author=verifier)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                        
                        with col_reopen:
                            reopen_reason = st.text_input(
                                "Reopen Reason",
                                key=f"reopen_reason_{defect['id']}",
                                placeholder="Why reopen?"
                            )
                            if st.button(f"🔄 Reopen", key=f"reopen_{defect['id']}"):
                                if not reopen_reason:
                                    st.error("Please provide a reason")
                                else:
                                    result = core.reopen_defect(defect['id'], reopen_reason, author=verifier if verifier else "Unknown")
                                    if result['success']:
                                        st.warning(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                    
                    elif defect['status'] == 'verified':
                        closer = st.text_input(
                            "Your Name",
                            key=f"closer_{defect['id']}",
                            placeholder="Your name"
                        )
                        if st.button(f"🔒 Close Defect", key=f"close_{defect['id']}", type="primary"):
                            if not closer:
                                st.error("Please enter your name")
                            else:
                                result = core.close_defect(defect['id'], author=closer)
                                if result['success']:
                                    st.success(result['message'])
                                    st.rerun()
                                else:
                                    st.error(result['message'])
    
    except Exception as e:
        st.error(f"Error loading defects: {e}")

# Tab 3: Defect History
with tab3:
    st.header("Defect History")
    
    try:
        all_defects = core.list_defects()
        
        if not all_defects:
            st.info("No defects found")
        else:
            # Create DataFrame for display
            df_data = []
            for defect in all_defects:
                df_data.append({
                    'ID': defect['id'],
                    'Title': defect['title'],
                    'Severity': defect['severity'].upper(),
                    'Status': defect['status'].replace('_', ' ').title(),
                    'Reported By': defect['reported_by'],
                    'Assigned To': defect.get('assigned_to', ''),
                    'Reported Date': defect['reported_date'][:10] if isinstance(defect['reported_date'], str) else str(defect['reported_date'])[:10],
                    'Affected Items': len(defect.get('affected_items', []))
                })
            
            df = pd.DataFrame(df_data)
            
            # Display metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Defects", len(all_defects))
            col2.metric("Open", len([d for d in all_defects if d['status'] in ['open', 'investigating']]))
            col3.metric("Critical", len([d for d in all_defects if d['severity'] == 'critical']))
            col4.metric("Resolved", len([d for d in all_defects if d['status'] in ['resolved', 'verified']]))
            col5.metric("Closed", len([d for d in all_defects if d['status'] == 'closed']))
            
            # Display table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Severity": st.column_config.TextColumn("Severity", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                }
            )
            
            # Export button
            if st.button("📥 Export to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"defects_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error loading defect history: {e}")

# Sidebar info
st.sidebar.title("Defect Tracking")
st.sidebar.info(
    """
    **IEC 62304 §9.7 Compliance**
    
    Problem Resolution Process:
    1. Report defect with details
    2. Assign to investigator
    3. Investigate and analyze root cause
    4. Resolve with fix
    5. Verify resolution works
    6. Close defect
    
    **Defect Lifecycle:**
    - Open → Investigating → Resolved → Verified → Closed
    - Can defer or reopen at any stage
    
    **Severity Levels:**
    - 🔴 Critical: Safety/data loss
    - 🟠 Major: Broken functionality
    - 🟡 Minor: Small issues
    - 🟢 Cosmetic: UI/UX only
    """
)
