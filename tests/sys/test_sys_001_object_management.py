import re
"""
Browser tests for SYS-001: Objects Management and Tracking

Verifies: The system shall support configurable objects (requirements, design items, 
change requests) to maintain a complete history.

@links: SYS-001
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_001_001_view_requirement_object(page: Page, streamlit_app):
    """
    TC-SYS-001-001: View Requirement Object
    
    @links: SYS-001
    @test_id: TC-SYS-001-001
    
    Verify system can display requirement objects with complete information.
    """
    # Navigate to SRS page with specific item
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    
    # Wait for Streamlit to actually render (app executes on first browser connection)
    # Look for Streamlit-specific elements that appear when app renders
    try:
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=10000)
    except:
        # If Streamlit container doesn't appear, wait a bit more
        page.wait_for_timeout(5000)
    
    # Debug: Check what's actually on the page
    page_content = page.content()
    if "SRS-001" not in page_content:
        print(f"\n[DEBUG] Page content preview (first 500 chars):")
        print(page_content[:500])
        page.screenshot(path="debug_srs_page.png")
        print("[DEBUG] Screenshot saved to debug_srs_page.png")
    
    # Verify requirement object is displayed with actual content from SRS-001.yaml
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify specific fields from SRS-001 are displayed
    page_content = page.content()
    
    # Check for title field
    assert "Item Persistence and Versioning" in page_content, "Should display SRS-001 title"
    
    # Check for content field - exact content from test data
    assert "Software shall persist items to YAML files" in page_content, \
        "Should display SRS-001 content from test data"
    
    # Check for status field
    assert "approved" in page_content or "Approved" in page_content, "Should display status: approved"


@pytest.mark.browser
def test_TC_SYS_001_002_view_change_request_object(page: Page, streamlit_app):
    """
    TC-SYS-001-002: View Change Request Object
    
    @links: SYS-001
    @test_id: TC-SYS-001-002
    
    Verify system can display change request objects.
    """
    # Navigate to CR page with specific item
    page.goto(f"{streamlit_app}/page_CR?item=CR-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify change request object is displayed with actual content from CR-001.yaml
    expect(page.get_by_role("heading", name="CR-001")).to_be_visible()
    
    # Verify specific fields from CR-001 are displayed
    page_content = page.content()
    
    # Check for title field
    assert "Test Change Request" in page_content, "Should display CR-001 title"
    
    # Check for description
    assert "Change request for testing purposes" in page_content, "Should display CR-001 description"
    
    # Check for affected items
    assert "SRS-001" in page_content, "Should display affected_items: SRS-001"
    
    # Check for status
    assert "approved" in page_content or "Approved" in page_content, "Should display status: approved"


@pytest.mark.browser
def test_TC_SYS_001_003_view_architecture_object(page: Page, streamlit_app):
    """
    TC-SYS-001-003: View Architecture Object
    
    @links: SYS-001
    @test_id: TC-SYS-001-003
    
    Verify system can display architecture/design objects.
    """
    # Navigate to SYSARCH page with specific item
    page.goto(f"{streamlit_app}/page_SYSARCH?item=SYSARCH-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify architecture object is displayed with actual content from SYSARCH-001.yaml
    expect(page.get_by_role("heading", name="SYSARCH-001")).to_be_visible()
    
    # Verify specific fields from SYSARCH-001 are displayed
    page_content = page.content()
    
    # Check for title field
    assert "System Architecture Component" in page_content, "Should display SYSARCH-001 title"
    
    # Check for content
    assert "Architecture component for test system" in page_content, "Should display SYSARCH-001 content"
    
    # Verify substantial architecture data is present
    assert len(page_content) > 2000, "Architecture object should contain substantial data"
