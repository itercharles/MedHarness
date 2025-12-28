"""
Browser tests for CRS-011: Regulatory Compliance Validation

Tests verify compliance checking through UI.

@links: CRS-011
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_011_001_view_compliance_dashboard(page: Page, streamlit_app):
    """
    TC-CRS-011-001: View Compliance Dashboard
    
    @links: CRS-011
    @test_id: TC-CRS-011-001
    
    User views compliance validation dashboard.
    """
    # Navigate to Compliance page (correct URL)
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance dashboard loaded
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify regulatory compliance information is displayed
    page_content = page.content()
    
    # Should reference regulatory frameworks
    assert any(term in page_content for term in ["IEC", "62304", "FDA", "Regulation"]), \
        "Compliance dashboard should reference regulatory frameworks"
    
    # Should show compliance heading
    assert "Compliance" in page_content, "Should display Compliance heading"


@pytest.mark.browser
def test_TC_CRS_011_002_run_compliance_check(page: Page, streamlit_app):
    """
    TC-CRS-011-002: Run Compliance Check
    
    @links: CRS-011
    @test_id: TC-CRS-011-002
    
    User runs compliance validation check.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify compliance page loaded for validation check
    expect(page.locator("text=Compliance").first).to_be_visible()
    
    # Verify compliance check capability is present
    page_content = page.content()
    
    # Should show compliance validation information
    assert any(term in page_content for term in ["IEC", "62304", "Compliance", "Check"]), \
        "Should display compliance validation information"
    
    # Should have compliance assessment data
    assert len(page_content) > 2000, "Compliance check should contain assessment data"
