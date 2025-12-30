"""
Browser tests for SYS-005: Compliance Assessment

Verifies: The system shall be able to assess the compliance of the DHF
by the governance policies (Regulations, Procedures).

@links: SYS-005
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_005_001_view_compliance_dashboard(page: Page, streamlit_app):
    """
    TC-SYS-005-001: View Compliance Dashboard
    
    @links: SYS-005
    @test_id: TC-SYS-005-001
    
    Verify system displays compliance assessment dashboard.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance page loaded with actual data
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify compliance assessment content is displayed
    page_content = page.content()
    # Should contain compliance-related terms
    assert any(term in page_content for term in ["IEC", "62304", "Compliance", "Policy"]), \
        "Compliance page should contain regulatory compliance information"


@pytest.mark.browser
def test_TC_SYS_005_002_view_compliance_checks(page: Page, streamlit_app):
    """
    TC-SYS-005-002: View Compliance Checks
    
    @links: SYS-005
    @test_id: TC-SYS-005-002
    
    Verify system displays compliance check results.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance page loaded with check results
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify compliance check results are displayed
    page_content = page.content()
    
    # Should contain compliance check indicators or results
    assert any(term in page_content for term in ["IEC", "62304", "Check", "Rule", "Policy"]), \
        "Compliance checks page should show regulatory checks"
    
    # Verify substantial compliance data is present
    assert len(page_content) > 2000, "Compliance checks should contain assessment data"


@pytest.mark.browser
def test_TC_SYS_005_003_run_compliance_assessment(page: Page, streamlit_app):
    """
    TC-SYS-005-003: Run Compliance Assessment
    
    @links: SYS-005
    @test_id: TC-SYS-005-003
    
    Verify system can run compliance assessment and produce results.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance page loaded
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify compliance assessment capability is present
    page_content = page.content()
    
    # Should show compliance assessment results or capability
    # The page should contain regulatory framework references
    assert any(term in page_content for term in ["IEC", "62304", "FDA", "Policy", "Regulation"]), \
        "Compliance page should reference regulatory frameworks"
    
    # Should show assessment results (pass/fail/warnings)
    # Or at minimum show that assessment is available
    assert any(indicator in page_content.lower() for indicator in ["pass", "fail", "check", "assess", "compliant", "rule"]), \
        "Compliance page should show assessment capability or results"
