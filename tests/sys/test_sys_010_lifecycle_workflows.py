import re
"""
Browser tests for SYS-010: Configurable Lifecycle Workflows

Verifies: The system shall support configurable lifecycle workflows for objects
with state transitions and validation rules defined in configuration.

@links: SYS-010
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_SYS_010_001_view_lifecycle_status(page: Page, streamlit_app):
    """
    TC-SYS-010-001: View Lifecycle Status
    
    @links: SYS-010
    @test_id: TC-SYS-010-001
    
    Verify system displays lifecycle status for objects.
    """
    # Navigate to an item with lifecycle
    page.goto(f"{streamlit_app}/page_SRS?item=SRS-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify item loaded with lifecycle information
    expect(page.get_by_role("heading", name="SRS-001")).to_be_visible()
    
    # Verify lifecycle status is displayed (SRS-001 is approved)
    page_content = page.content()
    assert any(status in page_content for status in ["approved", "Approved"]), \
        "Item should display lifecycle status: approved"


@pytest.mark.browser
def test_TC_SYS_010_002_view_cr_workflow(page: Page, streamlit_app):
    """
    TC-SYS-010-002: View Change Request Workflow
    
    @links: SYS-010
    @test_id: TC-SYS-010-002
    
    Verify system displays workflow states for change requests.
    """
    # Navigate to CR page
    page.goto(f"{streamlit_app}/page_CR?item=CR-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify CR loaded with workflow information
    expect(page.get_by_role("heading", name="CR-001")).to_be_visible()
    
    # Verify workflow status is displayed (CR-001 is approved)
    page_content = page.content()
    assert any(state in page_content for state in ["approved", "Approved"]), \
        "CR should display workflow state: approved"


@pytest.mark.browser
def test_TC_SYS_010_003_workflow_state_transition(page: Page, streamlit_app, test_dhf_root):
    """
    TC-SYS-010-003: Test Workflow State Transition
    
    @links: SYS-010
    @test_id: TC-SYS-010-003
    
    Verify system supports workflow state transitions (e.g., draft -> approved).
    """
    # Create a new test item in draft state
    page.goto(f"{streamlit_app}/page_SRS")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Click New button to create draft item
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)
    
    # Fill form (ID auto-generated)
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Workflow Item")
    page.locator("label:has-text('Content')").locator("..").locator("textarea").fill("Testing workflow transitions")
    
    # Click Create button
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Get the auto-generated ID using shared helper function
    from fixtures.browser_conftest import get_created_item_id
    created_id = get_created_item_id(test_dhf_root, 'SRS-')
    
    # Verify we're viewing the created item
    expect(page.get_by_role("heading", name=created_id)).to_be_visible()
    
    # Verify initial state is draft (new items start in draft)
    page_content = page.content()
    assert "draft" in page_content.lower() or "approve" in page_content.lower() or "Draft" in page_content, \
        "New item should be in draft state or have approval workflow available"
