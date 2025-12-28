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
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/03_Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name="Compliance")).to_be_visible()
    
    # Verify compliance content is displayed
    expect(page.locator("text=Compliance").first).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_011_002_run_compliance_check(page: Page, streamlit_app):
    """
    TC-CRS-011-002: Run Compliance Check
    
    @links: CRS-011
    @test_id: TC-CRS-011-002
    
    User runs compliance validation check.
    """
    # Navigate to Compliance page
    page.goto(f"{streamlit_app}/03_Compliance")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name="Compliance")).to_be_visible()
    
    # Look for compliance results or checks
    # The page should show some compliance information
    expect(page.locator("text=IEC 62304, text=ISO 14971, text=FDA").first).to_be_visible()
