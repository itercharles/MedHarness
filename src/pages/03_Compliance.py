"""Compliance Dashboard - Policy Validation and Compliance Checking"""

import streamlit as st
import pandas as pd
from pathlib import Path
from traceability.compliant_flow_core import CompliantFlowCore

# Page Configuration
st.set_page_config(
    page_title="Compliance - CompliantFlow",
    page_icon="✅",
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
st.title("✅ Compliance Dashboard")
st.markdown("### Regulatory Policy Validation and Compliance Checking")

# Load available policy groups
governance_dir = core.repo_root / "governance"
if not governance_dir.exists():
    st.warning("No governance directory found. Create `DHF/governance/` to add policy groups.")
    st.stop()

groups = [f.stem for f in governance_dir.glob("*.yaml")]

if not groups:
    st.info("No policy groups found in DHF/governance. Add YAML files to define compliance policies.")
    st.stop()

# Policy Group Selection
st.sidebar.header("Policy Groups")
selected_group = st.sidebar.selectbox(
    "Select Policy Group",
    groups,
    help="Choose a regulatory standard or policy group to validate"
)

# Display Group Details
group_data = core.get_policy_group(selected_group)

if not group_data:
    st.error(f"Failed to load policy group: {selected_group}")
    st.stop()

# Group Information
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(group_data.get('title', selected_group))
    st.caption(f"Version: {group_data.get('version', 'N/A')}")
with col2:
    if st.button("🔍 Check Compliance", type="primary", use_container_width=True):
        st.session_state['run_compliance'] = True

# Policies Overview
st.markdown("---")
st.markdown("### Defined Policies")

policies = group_data.get('policies', [])
if not policies:
    st.info("No policies defined in this group.")
else:
    # Create policy dataframe
    policy_df = pd.DataFrame(policies)
    
    # Display policy table
    st.dataframe(
        policy_df[['id', 'text', 'status']],
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("Policy ID", width="small"),
            "text": st.column_config.TextColumn("Policy Description", width="large"),
            "status": st.column_config.TextColumn("Status", width="small")
        },
        hide_index=True
    )
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Policies", len(policies))
    with col2:
        approved = len([p for p in policies if p.get('status') == 'approved'])
        st.metric("Approved Policies", approved)
    with col3:
        coverage = (approved / len(policies) * 100) if policies else 0
        st.metric("Policy Coverage", f"{coverage:.0f}%")

# Compliance Check Results
if st.session_state.get('run_compliance'):
    st.markdown("---")
    st.markdown("### Compliance Check Results")
    
    with st.spinner(f"Checking compliance against {selected_group}..."):
        report = core.check_compliance(selected_group)
    
    if not report:
        st.error("Failed to generate compliance report.")
        st.session_state['run_compliance'] = False
    else:
        # Overall Score
        score = report['score']
        
        # Color based on score
        if score >= 90:
            score_color = "🟢"
        elif score >= 70:
            score_color = "🟡"
        else:
            score_color = "🔴"
        
        st.markdown(f"## {score_color} Compliance Score: {score:.1f}%")
        st.progress(score / 100)
        
        # Results Table
        st.markdown("### Policy Validation Results")
        
        results_df = pd.DataFrame(report['results'])

        # Add status icon
        results_df['Icon'] = results_df['passed'].apply(lambda p: "✅" if p else "❌")

        # policy_text is now included in each result by the backend
        st.dataframe(
            results_df[['Icon', 'policy_id', 'policy_text', 'details']],
            use_container_width=True,
            column_config={
                "Icon": st.column_config.TextColumn("", width="small"),
                "policy_id": st.column_config.TextColumn("Policy ID", width="small"),
                "policy_text": st.column_config.TextColumn("Description", width="large"),
                "details": st.column_config.TextColumn("Validation Details", width="medium"),
            },
            hide_index=True,
        )
        
        # Detailed Evidence
        st.markdown("### Detailed Evidence")
        
        # Group by pass/fail
        passed_results = [r for r in report['results'] if r['passed']]
        failed_results = [r for r in report['results'] if not r['passed']]
        
        if failed_results:
            with st.expander(f"❌ Failed Policies ({len(failed_results)})", expanded=True):
                for res in failed_results:
                    st.markdown(f"**{res['policy_id']}**")
                    st.write(f"Details: {res['details']}")
                    if res.get('evidence'):
                        st.json(res['evidence'])
                    st.markdown("---")
        
        if passed_results:
            with st.expander(f"✅ Passed Policies ({len(passed_results)})"):
                for res in passed_results:
                    st.markdown(f"**{res['policy_id']}**")
                    st.write(f"Details: {res['details']}")
                    if res.get('evidence'):
                        st.json(res['evidence'])
                    st.markdown("---")

# Footer
st.markdown("---")
st.caption("Compliance Dashboard - Ensuring regulatory adherence through systematic validation")
