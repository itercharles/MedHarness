"""Review Dashboard for CompliantFlow."""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceability.compliant_flow_core import CompliantFlowCore

st.set_page_config(layout="wide", page_title="Review Dashboard - CompliantFlow")

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
st.title("📋 Review Dashboard")
st.markdown("Manage formal reviews and approvals per IEC 62304")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Create Review", "👀 My Reviews", "📊 Review History"])

# Tab 1: Create Review
with tab1:
    st.header("Create New Review")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Get all items for selection
        all_items = core.get_all_items()
        item_options = [item['id'] for item in all_items]
        
        item_id = st.selectbox(
            "Item to Review*",
            options=item_options,
            help="Select the item that needs review"
        )
        
    with col2:
        # Get applicable checklists
        checklist_options = ["None"]
        checklist_id = None
        
        if item_id:
            item_type = item_id.split('-')[0]
            try:
                checklists = core.checklist_engine.get_applicable_checklists(item_type)
                if checklists:
                    checklist_options = ["None"] + [f"{c.id} - {c.name}" for c in checklists]
            except Exception as e:
                st.warning(f"Could not load checklists: {e}")
            
            checklist_selection = st.selectbox(
                "Review Checklist (Optional)",
                options=checklist_options,
                help="Optional guidance checklist for reviewer"
            )
            
            if checklist_selection != "None":
                checklist_id = checklist_selection.split(' - ')[0]

    with st.form("create_review_form"):
        col1, col2 = st.columns(2)
        with col1:
            reviewer = st.text_input(
                "Assign to Reviewer*",
                placeholder="Reviewer Name",
                help="Name of person who will review this item"
            )
        
        with col2:
            created_by = st.text_input(
                "Your Name*",
                placeholder="Your Name",
                help="Person creating this review"
            )
        
        submit = st.form_submit_button("Create Review", type="primary")
    
    if submit:
        if not item_id or not reviewer or not created_by:
            st.error("Please fill in all required fields")
        else:
            try:
                result = core.create_review(item_id, reviewer, checklist_id, author=created_by)
                st.success(f"✅ Review {result['id']} created successfully!")
                st.info(f"💡 Review assigned to {reviewer}")
                
                # Show checklist if selected
                if checklist_id:
                    try:
                        checklist = core.checklist_engine.get_checklist(checklist_id)
                        if checklist:
                            with st.expander("📋 Review Guidance", expanded=True):
                                st.write(f"**{checklist.name}**")
                                if checklist.description:
                                    st.write(checklist.description)
                                st.write("**Guidance Points:**")
                                for point in checklist.guidance_points:
                                    st.write(f"- {point.text}")
                    except Exception as e:
                        st.warning(f"Could not load checklist: {e}")
            except Exception as e:
                st.error(f"Error creating review: {e}")

# Tab 2: My Reviews
with tab2:
    st.header("My Reviews")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        reviewer_filter = st.text_input("Filter by Reviewer", placeholder="Enter reviewer name")
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "pending", "in_review", "approved", "rejected", "needs_revision"],
            format_func=lambda x: x.replace('_', ' ').title() if x != "All" else "All"
        )
    
    try:
        # Get reviews
        if status_filter == "All":
            reviews = core.list_reviews(reviewer=reviewer_filter if reviewer_filter else None)
        else:
            reviews = core.list_reviews(status=status_filter, reviewer=reviewer_filter if reviewer_filter else None)
        
        if not reviews:
            st.info("No reviews found")
        else:
            st.write(f"Found {len(reviews)} review(s)")
            
            for review in reviews:
                with st.expander(
                    f"{review['id']}: {review['item_id']} - {review['status'].replace('_', ' ').title()}",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Item:** {review['item_id']}")
                        st.write(f"**Reviewer:** {review['reviewer']}")
                        st.write(f"**Status:** {review['status'].replace('_', ' ').title()}")
                        st.write(f"**Created:** {review['created_date'][:19] if isinstance(review['created_date'], str) else review['created_date']}")
                    
                    with col2:
                        if review.get('checklist_id'):
                            st.write(f"**Checklist:** {review['checklist_id']}")
                        if review.get('completed_date'):
                            st.write(f"**Completed:** {review['completed_date'][:19]}")
                        if review.get('comments'):
                            st.write(f"**Comments:** {review['comments']}")
                    
                    # Show checklist guidance if available
                    if review.get('checklist_id'):
                        try:
                            checklist = core.checklist_engine.get_checklist(review['checklist_id'])
                            if checklist:
                                st.write("**Review Guidance:**")
                                for point in checklist.guidance_points:
                                    st.write(f"- {point.text}")
                        except Exception as e:
                            st.warning(f"Could not load checklist: {e}")
                    
                    # Action buttons
                    if review['status'] == 'pending':
                        if st.button(f"▶️ Start Review", key=f"start_{review['id']}"):
                            from traceability.review.review_workflow import ReviewWorkflow
                            success, msg = ReviewWorkflow.start_review(core.review_tracker, review['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    elif review['status'] == 'in_review':
                        st.write("---")
                        comments = st.text_area(
                            "Review Comments",
                            key=f"comments_{review['id']}",
                            placeholder="Enter your review comments..."
                        )
                        
                        col_approve, col_reject, col_revision = st.columns(3)
                        
                        with col_approve:
                            if st.button(f"✅ Approve", key=f"approve_{review['id']}", type="primary"):
                                if not comments:
                                    st.error("Please enter comments")
                                else:
                                    result = core.approve_review(review['id'], comments, author=review['reviewer'])
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                        
                        with col_reject:
                            if st.button(f"❌ Reject", key=f"reject_{review['id']}"):
                                if not comments:
                                    st.error("Please enter rejection reason")
                                else:
                                    result = core.reject_review(review['id'], comments, author=review['reviewer'])
                                    if result['success']:
                                        st.warning(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                        
                        with col_revision:
                            if st.button(f"🔄 Request Revision", key=f"revision_{review['id']}"):
                                if not comments:
                                    st.error("Please enter revision request")
                                else:
                                    from traceability.review.review_workflow import ReviewWorkflow
                                    success, msg = ReviewWorkflow.request_revision(
                                        core.review_tracker, review['id'], comments, author=review['reviewer']
                                    )
                                    if success:
                                        st.info(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
    
    except Exception as e:
        st.error(f"Error loading reviews: {e}")

# Tab 3: Review History
with tab3:
    st.header("Review History")
    
    try:
        all_reviews = core.list_reviews()
        
        if not all_reviews:
            st.info("No reviews found")
        else:
            # Create DataFrame
            df_data = []
            for review in all_reviews:
                df_data.append({
                    'ID': review['id'],
                    'Item': review['item_id'],
                    'Reviewer': review['reviewer'],
                    'Status': review['status'].replace('_', ' ').title(),
                    'Created': review['created_date'][:10] if isinstance(review['created_date'], str) else str(review['created_date'])[:10],
                    'Completed': review['completed_date'][:10] if review.get('completed_date') and isinstance(review['completed_date'], str) else ''
                })
            
            df = pd.DataFrame(df_data)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Reviews", len(all_reviews))
            col2.metric("Pending", len([r for r in all_reviews if r['status'] in ['pending', 'in_review']]))
            col3.metric("Approved", len([r for r in all_reviews if r['status'] == 'approved']))
            col4.metric("Needs Action", len([r for r in all_reviews if r['status'] == 'needs_revision']))
            
            # Display table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export button
            if st.button("📥 Export to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"reviews_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error loading review history: {e}")

# Sidebar info
st.sidebar.title("Review Dashboard")
st.sidebar.info(
    """
    **IEC 62304 Compliance**
    
    Formal review and approval workflow:
    1. Create review for item
    2. Assign to reviewer
    3. Reviewer uses guidance checklist
    4. Approve/Reject/Request Revision
    5. Track in history
    
    **Review States:**
    - Pending: Awaiting review
    - In Review: Being reviewed
    - Approved: Accepted
    - Rejected: Not accepted
    - Needs Revision: Changes requested
    """
)
