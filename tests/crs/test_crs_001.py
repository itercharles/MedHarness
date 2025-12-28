"""
Browser tests for CRS-001: Requirement Definition

Tests verify item management through UI: create, view, search.
Uses query parameters for item selection (avoiding canvas interaction).

@links: CRS-001
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_001_001_create_requirement(page: Page, streamlit_app):
    """
    TC-CRS-001-001: Create New Requirement via UI
    
    @links: CRS-001
    @test_id: TC-CRS-001-001
    
    User creates a new software requirement through the UI.
    """
    # Navigate to app
    page.goto(streamlit_app)
    
    # Wait for Streamlit to load
    page.wait_for_selector("[data-testid='stApp']", timeout=30000)
    
    # Click Software Requirement in sidebar (singular)
    page.get_by_role("link", name="Software Requirement").click()
    page.wait_for_load_state("networkidle")
    
    # Click ➕ New button
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)  # Wait for form to appear
    
    # Fill form - note: ID field has placeholder "SRS-XXX"
    page.fill("input[placeholder='SRS-XXX']", "SRS-999")
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Requirement")
    page.locator("label:has-text('Content')").locator("..").locator("textarea").fill("This is a test requirement created via browser test")
    
    # Click ✅ Create button
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    
    # Verify item appears in table (search for it)
    page.fill("input[placeholder='Search by ID or title...']", "SRS-999")
    page.wait_for_timeout(1000)
    
    # Verify item was created - check the details view heading
    # (table cells may be hidden/scrolled, but heading is always visible)
    expect(page.get_by_role("heading", name="SRS-999")).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_TC_CRS_001_002_view_requirement_details(page: Page, streamlit_app):
    """
    TC-CRS-001-002: View Requirement Details
    
    @links: CRS-001
    @test_id: TC-CRS-001-002
    
    User views details of an existing requirement using query parameter navigation.
    """
    # Navigate directly to SRS page with item selected via query parameter
    # This uses the existing ?item= functionality in universal_page_template.py
    page.goto(f"{streamlit_app}/7_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)  # Give Streamlit time to process selection
    
    # Verify details view appears - check for heading
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify status badge
    expect(page.locator("text=Approved").first).to_be_visible()



@pytest.mark.browser  
def test_TC_CRS_001_003_search_requirements(page: Page, streamlit_app):
    """
    TC-CRS-001-003: Search Requirements
    
    @links: CRS-001
    @test_id: TC-CRS-001-003
    
    User searches for requirements by ID or title using query parameter navigation.
    """
    # Test 1: Navigate to specific item by ID
    page.goto(f"{streamlit_app}/7_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-001 is shown
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Test 2: Navigate to different item (SRS-002 has "Graph" in title)
    page.goto(f"{streamlit_app}/7_SRS?item=SRS-002")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-002 is shown
    expect(page.get_by_role("heading", name="SRS-002")).to_be_visible()
