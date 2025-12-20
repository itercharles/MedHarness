"""Manual Test Management Page - Update and track manual test verification."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from traceability.compliant_flow_core import CompliantFlowCore

# Page Configuration
st.set_page_config(
    page_title="Manual Testing - CompliantFlow",
    page_icon="👤",
    layout="wide"
)

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

# Header
st.title("👤 Manual Test Management")
st.markdown("### Update and Track Manual Test Verification")

# Get all test cases
all_items = core.get_all_items()

# Filter for manual test cases
manual_tests = [
    item for item in all_items
    if item['id'].startswith(('TC-', 'tc-')) and item.get('test_type') == 'manual'
]

if not manual_tests:
    st.info("No manual test cases found. Add `test_type: manual` to test case YAML files.")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

# Status filter
all_statuses = ['PENDING', 'PASS', 'FAIL', 'SKIP']
selected_statuses = st.sidebar.multiselect(
    "Verification Status",
    all_statuses,
    default=all_statuses
)

# Filter tests
filtered_tests = [
    test for test in manual_tests
    if test.get('verification_status', 'PENDING') in selected_statuses
]

# Statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Manual Tests", len(manual_tests))
with col2:
    passed = len([t for t in manual_tests if t.get('verification_status') == 'PASS'])
    st.metric("Passed", passed)
with col3:
    failed = len([t for t in manual_tests if t.get('verification_status') == 'FAIL'])
    st.metric("Failed", failed)
with col4:
    pending = len([t for t in manual_tests if t.get('verification_status', 'PENDING') == 'PENDING'])
    st.metric("Pending", pending)

st.markdown("---")

# Test list
st.subheader(f"Manual Test Cases ({len(filtered_tests)})")

# Create dataframe for display
test_data = []
for test in filtered_tests:
    test_data.append({
        'ID': test['id'],
        'Title': test.get('title', ''),
        'Status': test.get('verification_status', 'PENDING'),
        'Verified By': test.get('verified_by', '-'),
        'Date': test.get('verified_date', '-'),
    })

if test_data:
    df = pd.DataFrame(test_data)
    
    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "ID": st.column_config.TextColumn("Test ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Verified By": st.column_config.TextColumn("Verified By", width="medium"),
            "Date": st.column_config.TextColumn("Verification Date", width="small"),
        },
        hide_index=True
    )
    
    st.markdown("---")
    
    # Update test status section
    st.subheader("Update Test Verification")
    
    # Select test to update
    test_ids = [t['id'] for t in filtered_tests]
    selected_test_id = st.selectbox("Select Test Case", test_ids)
    
    if selected_test_id:
        # Find selected test
        selected_test = next((t for t in filtered_tests if t['id'] == selected_test_id), None)
        
        if selected_test:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**{selected_test.get('title', 'No title')}**")
                st.caption(selected_test.get('content', 'No description'))
            
            with col2:
                current_status = selected_test.get('verification_status', 'PENDING')
                st.info(f"Current Status: **{current_status}**")
            
            # Update form
            with st.form("update_verification"):
                new_status = st.selectbox(
                    "New Status",
                    ['PENDING', 'PASS', 'FAIL', 'SKIP'],
                    index=['PENDING', 'PASS', 'FAIL', 'SKIP'].index(current_status)
                )
                
                verified_by = st.text_input(
                    "Verified By",
                    value=selected_test.get('verified_by', ''),
                    placeholder="Your name"
                )
                
                verification_notes = st.text_area(
                    "Verification Notes",
                    value=selected_test.get('verification_notes', ''),
                    placeholder="Add any notes about the test execution..."
                )
                
                submitted = st.form_submit_button("Update Verification Status", type="primary")
                
                if submitted:
                    if not verified_by and new_status != 'PENDING':
                        st.error("Please provide your name in 'Verified By' field")
                    else:
                        st.warning("⚠️ **Manual update not yet implemented**")
                        st.info("""
                        To update test status manually:
                        1. Edit the test case YAML file directly
                        2. Add/update these fields:
                           ```yaml
                           verification_status: {status}
                           verified_by: "{name}"
                           verified_date: "{date}"
                           verification_notes: "{notes}"
                           ```
                        3. Commit the changes to Git
                        """.format(
                            status=new_status,
                            name=verified_by,
                            date=datetime.now().strftime('%Y-%m-%d'),
                            notes=verification_notes
                        ))
                        
                        # TODO: Implement actual YAML file update
                        # TODO: Append to audit log
else:
    st.info("No manual tests match the selected filters.")

# Footer
st.markdown("---")
st.caption("Manual Test Management - Track verification of manual test cases")
