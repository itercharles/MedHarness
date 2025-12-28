"""
Browser tests for CRS-008: Automated Test Integration

Tests verify test result integration through UI.

@links: CRS-008
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_008_001_view_test_coverage(page: Page, streamlit_app):
    """
    TC-CRS-008-001: View Test Coverage
    
    @links: CRS-008
    @test_id: TC-CRS-008-001
    
    User views test coverage for a requirement.
    """
    # Navigate to SRS-001 detail page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=Software Requirements")
    page.wait_for_load_state("networkidle")
    
    # Click on SRS-001
    page.click("text=SRS-001")
    page.wait_for_load_state("networkidle")
    
    # Scroll to Test Coverage section
    page.locator("text=Test Coverage").scroll_into_view_if_needed()
    
    # Verify test cases are listed
    expect(page.locator("text=test_srs_001")).to_be_visible()
    
    # Verify pass/fail status shown
    expect(page.locator("text=✓, text=✗, text=passed, text=failed")).to_have_count_greater_than(0)
    
    # Click test case link
    page.click("a:has-text('test_srs_001'):first")
    page.wait_for_load_state("networkidle")
    
    # Verify navigated to test details
    expect(page.locator("h1:has-text('test_srs_001')")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_008_002_view_coverage_dashboard(page: Page, streamlit_app):
    """
    TC-CRS-008-002: View Coverage Dashboard
    
    @links: CRS-008
    @test_id: TC-CRS-008-002
    
    User views overall test coverage metrics on dashboard.
    """
    # Navigate to Dashboard or Compliance page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=Dashboard, text=Compliance")
    page.wait_for_load_state("networkidle")
    
    # Locate Test Coverage widget
    coverage_widget = page.locator("text=Test Coverage").locator("..")
    expect(coverage_widget).to_be_visible()
    
    # Verify percentage displayed
    expect(page.locator("text=/\\d+%/")).to_be_visible()
    
    # Verify breakdown by doc type
    expect(page.locator("text=SRS, text=SYS")).to_be_visible()
    
    # Click View Details
    page.click("button:has-text('View Details, View Uncovered')")
    page.wait_for_load_state("networkidle")
    
    # Verify shows uncovered requirements
    expect(page.locator("text=Uncovered Requirements, text=Not Verified")).to_be_visible()
