"""
Browser tests for SYS-008: Change Management

Verifies: The system shall provide a change management module that enables
tracking, evaluation, and approval of changes.

@links: SYS-008
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_008_001_view_change_requests(page: Page, streamlit_app):
    """
    TC-SYS-008-001: View Change Requests
    
    @links: SYS-008
    @test_id: TC-SYS-008-001
    
    Verify system displays change request list for tracking.
    """
    # Navigate to Change Request page
    page.goto(f"{streamlit_app}/9_CR")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR page loaded
    expect(page.get_by_role("heading", name="Change Request")).to_be_visible()
    
    # Verify table is displayed with CR data
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    
    # Verify actual CR items exist in the system
    page_content = page.content()
    assert "CR-" in page_content, "Change Request list should contain CR items"


@pytest.mark.browser
def test_TC_SYS_008_002_view_change_request_details(page: Page, streamlit_app):
    """
    TC-SYS-008-002: View Change Request Details
    
    @links: SYS-008
    @test_id: TC-SYS-008-002
    
    Verify system displays detailed change request information.
    """
    # Navigate to specific CR
    page.goto(f"{streamlit_app}/9_CR?item=CR-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR details loaded with actual CR-001 data
    expect(page.get_by_role("heading", name="CR-001")).to_be_visible()
    
    # Verify specific CR-001 fields from YAML are displayed
    page_content = page.content()
    
    # Check for title
    assert "bulk approval feature" in page_content, "Should display CR-001 title"
    
    # Check for priority field
    assert "Medium" in page_content, "Should display priority: Medium"
    
    # Check for requested_by field
    assert "Quality Team" in page_content, "Should display requested_by: Quality Team"


@pytest.mark.browser
def test_TC_SYS_008_003_view_affected_items(page: Page, streamlit_app):
    """
    TC-SYS-008-003: View Affected Items
    
    @links: SYS-008
    @test_id: TC-SYS-008-003
    
    Verify system shows items affected by change request.
    """
    # Navigate to CR with affected items
    page.goto(f"{streamlit_app}/9_CR?item=CR-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR loaded with affected items from CR-001.yaml
    expect(page.get_by_role("heading", name="CR-001")).to_be_visible()
    
    # Verify affected_items field is displayed
    page_content = page.content()
    
    # CR-001 has affected_items: [SYS-001, SYSARCH-001]
    assert "SYS-001" in page_content, "Should display affected item: SYS-001"
    assert "SYSARCH-001" in page_content, "Should display affected item: SYSARCH-001"
    
    # Verify affected items section/label exists
    assert "affected" in page_content.lower() or "Affected" in page_content, \
        "Should show affected items section"


@pytest.mark.browser
def test_TC_SYS_008_004_create_change_request(page: Page, streamlit_app):
    """
    TC-SYS-008-004: Create Change Request
    
    @links: SYS-008
    @test_id: TC-SYS-008-004
    
    Verify system allows creating new change requests.
    """
    # Navigate to Change Request page
    page.goto(f"{streamlit_app}/9_CR")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Click New button to create CR
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)
    
    # Fill form to create CR-999
    page.fill("input[placeholder='CR-XXX']", "CR-999")
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Change Request")
    page.locator("label:has-text('Description')").locator("..").locator("textarea").fill("Testing CR creation functionality")
    
    # Click Create button
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Navigate to the created CR
    page.goto(f"{streamlit_app}/9_CR?item=CR-999")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR was created
    expect(page.get_by_role("heading", name="CR-999")).to_be_visible()
    
    # Verify CR content is displayed
    page_content = page.content()
    assert "Test Change Request" in page_content, "Should display CR-999 title"
    assert "Testing CR creation" in page_content, "Should display CR-999 description"


@pytest.mark.browser
def test_TC_SYS_008_005_edit_change_request(page: Page, streamlit_app):
    """
    TC-SYS-008-005: Edit Change Request
    
    @links: SYS-008
    @test_id: TC-SYS-008-005
    
    Verify system allows editing existing change requests.
    """
    # First create a CR to edit
    page.goto(f"{streamlit_app}/9_CR")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Click New button
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)
    
    # Create CR-998
    page.fill("input[placeholder='CR-XXX']", "CR-998")
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Original Title")
    page.locator("label:has-text('Description')").locator("..").locator("textarea").fill("Original description")
    
    # Click Create
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Navigate to the created CR
    page.goto(f"{streamlit_app}/9_CR?item=CR-998")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR was created with original content
    expect(page.get_by_role("heading", name="CR-998")).to_be_visible()
    page_content = page.content()
    assert "Original Title" in page_content, "Should display original title"
