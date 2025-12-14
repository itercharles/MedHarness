"""Release Management page for CompliantFlow."""

import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceability.compliant_flow_core import CompliantFlowCore



def get_core():
    """Get CompliantFlowCore instance (not cached to allow data reloading)."""
    dhf_root = Path(__file__).parent.parent.parent / "DHF"
    return CompliantFlowCore(dhf_root)



st.set_page_config(page_title="Release Management", page_icon="🚀", layout="wide")

st.title("🚀 Release Management")
st.markdown("Track and validate software releases per IEC 62304 §5.8")

# Initialize core
core = get_core()

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Create Release", "📊 Manage Releases", "📄 Release Reports"])

# Tab 1: Create Release
with tab1:
    st.header("Create New Release")
    
    with st.form("create_release_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            version = st.text_input(
                "Version *",
                placeholder="e.g., 1.0.0",
                help="Semantic version number"
            )
            release_date = st.date_input(
                "Target Release Date",
                value=date.today()
            )
            created_by = st.text_input(
                "Created By *",
                placeholder="Your name"
            )
        
        with col2:
            # Get all change requests for multiselect
            try:
                all_crs = core.list_change_requests()
                cr_ids = [cr['id'] for cr in all_crs]
                
                included_change_requests = st.multiselect(
                    "Included Change Requests *",
                    options=cr_ids,
                    help="Select change requests to include in this release"
                )
            except:
                st.warning("Change request tracking not available")
                included_change_requests = []
            
            tags = st.text_input(
                "Tags",
                placeholder="e.g., major, patch, hotfix (comma-separated)"
            )
        
        release_notes = st.text_area(
            "Release Notes",
            placeholder="Describe what's new in this release...",
            height=150
        )
        
        submitted = st.form_submit_button("Create Release", type="primary")
        
        if submitted:
            if not version or not created_by:
                st.error("Version and Created By are required")
            elif not included_change_requests:
                st.error("At least one change request must be included")
            else:
                try:
                    release_data = {
                        'version': version,
                        'release_date': release_date,
                        'created_by': created_by,
                        'included_change_requests': included_change_requests,
                        'release_notes': release_notes,
                        'tags': [t.strip() for t in tags.split(',')] if tags else []
                    }
                    
                    release = core.create_release(release_data, author=created_by)
                    st.success(f"✅ Release {version} created successfully!")
                    st.json(release)
                except Exception as e:
                    st.error(f"Failed to create release: {e}")

# Tab 2: Manage Releases
with tab2:
    st.header("Manage Releases")
    
    # Filters
    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All", "planning", "in_progress", "testing", "approved", "released"]
        )
    
    # Get releases
    try:
        if status_filter == "All":
            releases = core.list_releases()
        else:
            releases = core.list_releases(status=status_filter)
        
        if not releases:
            st.info("No releases found")
        else:
            for release in releases:
                with st.expander(f"🚀 **{release['version']}** - {release['status'].upper()}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Status:**", release['status'])
                        st.write("**Created By:**", release['created_by'])
                        if release.get('approved_by'):
                            st.write("**Approved By:**", release['approved_by'])
                    
                    with col2:
                        if release.get('release_date'):
                            st.write("**Release Date:**", release['release_date'])
                        cr_count = len(release.get('included_change_requests', []))
                        st.write("**Change Requests:**", cr_count)
                        if cr_count > 0:
                            st.write("**CRs:**", ", ".join(release.get('included_change_requests', [])[:3]))
                            if cr_count > 3:
                                st.write(f"  ... and {cr_count - 3} more")
                        if release.get('tags'):
                            st.write("**Tags:**", ", ".join(release['tags']))
                    
                    with col3:
                        # Reserved for future use
                        pass
                    
                    # Release notes
                    if release.get('release_notes'):
                        st.markdown("**Release Notes:**")
                        st.markdown(release['release_notes'])
                    
                    # Actions based on status
                    st.markdown("---")
                    st.markdown("**Workflow Status:**")
                    
                    # Show current workflow state
                    workflow_states = {
                        'planning': '📝 **Planning** → 💻 Developing → 🧪 Testing → 🚀 Released',
                        'developing': '📝 Planning → 💻 **Developing** → 🧪 Testing → 🚀 Released',
                        'testing': '📝 Planning → 💻 Developing → 🧪 **Testing** → 🚀 Released',
                        'released': '📝 Planning → 💻 Developing → 🧪 Testing → 🚀 **Released**'
                    }
                    st.caption(workflow_states.get(release['status'], ''))
                    
                    # Initialize criteria checker
                    from traceability.release.workflow_criteria import WorkflowCriteriaChecker
                    criteria_config = Path(__file__).parent.parent.parent / "DHF" / "config" / "workflow_criteria.yaml"
                    criteria_checker = WorkflowCriteriaChecker(criteria_config, core)
                    
                    # Show criteria for next transition
                    current_status = release['status']
                    
                    if current_status == 'planning':
                        st.markdown("#### Criteria to Start Development:")
                        can_transition, criteria_results = criteria_checker.check_transition_criteria(
                            release, 'planning', 'developing'
                        )
                        
                        for criterion in criteria_results:
                            if criterion['passed']:
                                st.success(f"✅ {criterion['name']}: {criterion['message']}")
                            else:
                                st.error(f"❌ {criterion['name']}: {criterion['message']}")
                        
                        # Stage transition approval
                        if can_transition:
                            st.markdown("---")
                            st.markdown("**Stage Transition Approval:**")
                            approver = st.text_input(
                                "Approved by *",
                                key=f"approver_plan_dev_{release['version']}",
                                placeholder="Enter approver name"
                            )
                            if st.button(f"💻 Approve & Start Development", key=f"developing_{release['version']}", type="primary"):
                                if approver:
                                    from traceability.models.release import ReleaseStatus
                                    from datetime import datetime
                                    
                                    # Record stage approval
                                    stage_approvals = release.get('stage_approvals', {})
                                    stage_approvals['planning_to_developing'] = {
                                        'approved_by': approver,
                                        'approved_date': datetime.now().isoformat()
                                    }
                                    
                                    core.release_tracker.update_release(
                                        release['version'],
                                        {
                                            'status': ReleaseStatus.DEVELOPING,
                                            'stage_approvals': stage_approvals
                                        }
                                    )
                                    st.success(f"Approved by {approver}. Status updated to Developing")
                                    st.rerun()
                                else:
                                    st.warning("Please enter approver name")
                        else:
                            st.warning("⚠️ All criteria must be met before stage transition.")
                    
                    elif current_status == 'developing':
                        st.markdown("#### Criteria to Start Testing:")
                        can_transition, criteria_results = criteria_checker.check_transition_criteria(
                            release, 'developing', 'testing'
                        )
                        
                        # Import reusable UI components
                        from ui_components import render_criteria_checklist, render_stage_approval
                        
                        # Define verification callback
                        def on_verify(criterion_id, verifier, notes, item_id):
                            from datetime import datetime
                            manual_verifications = release.get('manual_verifications', {})
                            manual_verifications[criterion_id] = {
                                'verified_by': verifier,
                                'verified_date': datetime.now().isoformat(),
                                'notes': notes
                            }
                            core.release_tracker.update_release(
                                item_id,
                                {'manual_verifications': manual_verifications}
                            )
                            st.toast(f"✅ Verified by {verifier}", icon="✅")
                            st.rerun()
                        
                        # Render criteria checklist with manual verifications
                        render_criteria_checklist(
                            criteria_results,
                            release['version'],
                            release.get('manual_verifications', {}),
                            on_verify
                        )
                        
                        # Stage transition approval
                        if can_transition:
                            def on_approve(approver, item_id):
                                from traceability.models.release import ReleaseStatus
                                from datetime import datetime
                                
                                stage_approvals = release.get('stage_approvals', {})
                                stage_approvals['developing_to_testing'] = {
                                    'approved_by': approver,
                                    'approved_date': datetime.now().isoformat()
                                }
                                
                                core.release_tracker.update_release(
                                    item_id,
                                    {
                                        'status': ReleaseStatus.TESTING,
                                        'stage_approvals': stage_approvals
                                    }
                                )
                                st.success(f"Approved by {approver}. Status updated to Testing")
                                st.rerun()
                            
                            render_stage_approval(
                                'developing_to_testing',
                                release['version'],
                                on_approve,
                                "🧪 Approve & Start Testing"
                            )
                        else:
                            st.warning("⚠️ All criteria must be met before stage transition.")
                    
                    elif current_status == 'testing':
                        st.markdown("#### Testing & Release Criteria:")
                        
                        # Auto-run validation if not already done
                        if not release.get('validation_passed') and not release.get('validation_report'):
                            with st.spinner("Running validation..."):
                                result = core.validate_release(release['version'])
                                st.rerun()
                        
                        # Show release criteria
                        can_release, release_criteria = criteria_checker.check_transition_criteria(
                            release, 'testing', 'released'
                        )
                        
                        st.markdown("**Release Checklist:**")
                        for criterion in release_criteria:
                            severity = criterion.get('severity', 'error')
                            if criterion['passed']:
                                st.success(f"✅ {criterion['name']}: {criterion['message']}")
                            elif severity == 'warning':
                                st.warning(f"⚠️ {criterion['name']}: {criterion['message']}")
                            else:
                                st.error(f"❌ {criterion['name']}: {criterion['message']}")
                        
                        # Release button - only if criteria met
                        if can_release:
                            st.markdown("---")
                            st.markdown("**Release Approval:**")
                            col1, col2 = st.columns(2)
                            with col1:
                                approver = st.text_input(
                                    "Approved by *",
                                    key=f"approver_{release['version']}",
                                    placeholder="Enter approver name"
                                )
                            with col2:
                                releaser = st.text_input(
                                    "Released by *",
                                    key=f"releaser_{release['version']}",
                                    placeholder="Enter your name"
                                )
                            
                            if st.button(f"🚀 Approve & Release", key=f"release_{release['version']}", type="primary"):
                                if approver and releaser:
                                    from datetime import datetime
                                    
                                    # Record stage approval
                                    stage_approvals = release.get('stage_approvals', {})
                                    stage_approvals['testing_to_released'] = {
                                        'approved_by': approver,
                                        'approved_date': datetime.now().isoformat()
                                    }
                                    
                                    # Update with approver first
                                    core.release_tracker.update_release(
                                        release['version'],
                                        {
                                            'approved_by': approver,
                                            'stage_approvals': stage_approvals
                                        }
                                    )
                                    # Then mark as released
                                    result = core.mark_released(release['version'], releaser)
                                    if result['success']:
                                        st.success(result['message'])
                                        st.rerun()
                                    else:
                                        st.error(result['message'])
                                else:
                                    st.warning("Please enter both approver and releaser names")
                        else:
                            st.info("⚠️ All criteria must be met before release.")
                    
                    elif current_status == 'released':
                        st.success("🎉 This release has been finalized!")
                        if release.get('released_date'):
                            st.info(f"Released on: {release['released_date']}")
                        if release.get('approved_by'):
                            st.info(f"Approved by: {release['approved_by']}")
    
    except Exception as e:
        st.error(f"Error loading releases: {e}")

# Tab 3: Release Reports
with tab3:
    st.header("Release Reports")
    
    try:
        releases = core.list_releases()
        if releases:
            selected_version = st.selectbox(
                "Select Release",
                options=[r['version'] for r in releases]
            )
            
            if selected_version:
                release = core.get_release(selected_version)
                
                if release:
                    st.subheader(f"Release {release['version']} Report")
                    
                    # Summary
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Status", release['status'].upper())
                    with col2:
                        cr_count = len(release.get('included_change_requests', []))
                        st.metric("Change Requests", cr_count)
                    with col3:
                        validation = "✅ PASS" if release.get('validation_passed') else "❌ FAIL"
                        st.metric("Validation", validation)
                    with col4:
                        if release.get('release_date'):
                            st.metric("Release Date", release['release_date'])
                    
                    # Validation Report
                    if release.get('validation_report'):
                        st.markdown("### Validation Report")
                        report = release['validation_report']
                        
                        # Change Requests
                        if 'change_requests' in report and report['change_requests'].get('total_change_requests', 0) > 0:
                            st.markdown("**Change Requests:**")
                            cr = report['change_requests']
                            st.write(f"- Total: {cr.get('total_change_requests', 0)}")
                            st.write(f"- Approved: {cr.get('approved', 0)}")
                            if cr.get('not_approved', 0) > 0:
                                st.error(f"⚠️ {cr['not_approved']} change request(s) not approved")
                                for item in cr.get('not_approved_details', []):
                                    st.write(f"  - {item['id']}: {item['status']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Requirement Coverage:**")
                            if 'requirement_coverage' in report:
                                cov = report['requirement_coverage']
                                st.write(f"- Total Requirements: {cov.get('total_requirements', 0)}")
                                st.write(f"- Covered: {cov.get('covered', 0)}")
                                st.write(f"- Coverage: {cov.get('coverage_percentage', 0):.1f}%")
                        
                        with col2:
                            st.markdown("**Test Status:**")
                            if 'test_status' in report:
                                tests = report['test_status']
                                st.write(f"- Total Tests: {tests.get('total_tests', 0)}")
                                st.write(f"- Passed: {tests.get('passed', 0)}")
                                st.write(f"- Pass Rate: {tests.get('pass_percentage', 0):.1f}%")
                    
                    # Release Notes
                    if release.get('release_notes'):
                        st.markdown("### Release Notes")
                        st.markdown(release['release_notes'])
                    
                    # Export
                    st.markdown("---")
                    if st.button("📥 Export Report"):
                        st.download_button(
                            label="Download as JSON",
                            data=str(release),
                            file_name=f"release_{selected_version}_report.json",
                            mime="application/json"
                        )
        else:
            st.info("No releases available")
    
    except Exception as e:
        st.error(f"Error loading release reports: {e}")
