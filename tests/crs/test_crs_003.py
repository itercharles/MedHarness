"""
Browser tests for CRS-003: Change Control

Tests verify change control workflow through UI.

@links: CRS-003
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_003_001_view_change_requests(page: Page, streamlit_app):
    """
    TC-CRS-003-001: View Change Requests
    
    @links: CRS-003
    @test_id: TC-CRS-003-001
    
    User views list of change requests.
    """
    # Navigate to Change Request page
    page.goto(f"{streamlit_app}/9_CR")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name="Change Request")).to_be_visible()
    
    # Verify table is displayed
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_003_002_create_change_request(page: Page, streamlit_app):
    """
    TC-CRS-003-002: Create Change Request
    
    @links: CRS-003
    @test_id: TC-CRS-003-002
    
    User creates a new change request through UI.
    """
    # Navigate to Change Request page
    page.goto(f"{streamlit_app}/9_CR")
    page.wait_for_load_state("networkidle")
    
    # Click New button
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)
    
    # Fill form
    page.fill("input[placeholder='CR-XXX']", "CR-999")
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Change Request")
    page.locator("label:has-text('Description')").locator("..").locator("textarea").fill("Test change request for browser testing")
    
    # Click Create button
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    
    # Verify CR was created
    page.fill("input[placeholder='Search by ID or title...']", "CR-999")
    page.wait_for_timeout(1000)
    expect(page.get_by_role("heading", name="CR-999")).to_be_visible()
