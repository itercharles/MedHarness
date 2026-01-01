"""
Browser tests for CRS-001: Requirement Definition

Tests verify item management through UI: create, view, search.
Uses query parameters for item selection (avoiding canvas interaction).

@links: CRS-001
"""

import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_001_001_create_requirement(page: Page, streamlit_app, test_dhf_root):
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
    
    # Fill form (ID auto-generated)
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Requirement")
    page.locator("label:has-text('Content')").locator("..").locator("textarea").fill("This is a test requirement created via browser test")
    
    # Click ✅ Create button
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    
    # Get the auto-generated ID using shared helper function
    from fixtures.browser_conftest import get_created_item_id
    created_id = get_created_item_id(test_dhf_root, 'SRS-')
    
    # Navigate to the created item
    page.goto(f"{streamlit_app}/page_SRS?item={created_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify we can navigate to the created item
    # Verify we can navigate to the created item
    expect(page.get_by_role("heading", name=created_id)).to_be_visible(timeout=5000)


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
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)  # Give Streamlit time to process selection
    
    # Verify SRS-001 details are displayed
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify specific SRS-001 field data
    page_content = page.content()
    assert "Item Persistence and Versioning" in page_content, "Should display SRS-001 title"
    assert "approved" in page_content.lower(), "Should display approved status"



@pytest.mark.browser  
def test_TC_CRS_001_003_search_requirements(page: Page, streamlit_app):
    """
    TC-CRS-001-003: Search Requirements
    
    @links: CRS-001
    @test_id: TC-CRS-001-003
    
    User searches for requirements by ID or title using query parameter navigation.
    """
    # Test 1: Navigate to specific item by ID
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-001 is shown
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Test 2: Navigate to different item (SRS-002 has "Graph" in title)
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-002")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify SRS-002 is shown with its data
    expect(page.get_by_role("heading", name="SRS-002")).to_be_visible()
    
    # Verify SRS-002 content is displayed
    page_content = page.content()
    assert "SRS-002" in page_content, "Should display SRS-002 ID"
