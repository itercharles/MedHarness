"""
Browser tests for CRS-005: Architecture Definition

Tests verify architecture management through UI: add, edit, approve.

@links: CRS-005
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_005_001_add_architecture_item(page: Page, streamlit_app):
    """
    TC-CRS-005-001: Add Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-001
    
    User adds a new system architecture item through the UI.
    """
    # Navigate to System Architecture page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=System Architecture")
    page.wait_for_load_state("networkidle")
    
    # Click Create New Item
    page.click("button:has-text('Create New Item')")
    
    # Fill form
    page.fill("input[aria-label='Title']", "Test Architecture Component")
    page.fill("textarea[aria-label='Content']", "This is a test architecture component")
    page.select_option("select[aria-label='Component Type']", "module")
    
    # Save
    page.click("button:has-text('Save')")
    page.wait_for_load_state("networkidle")
    
    # Verify item appears in table
    expect(page.locator("text=Test Architecture Component")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_005_002_edit_architecture_item(page: Page, streamlit_app):
    """
    TC-CRS-005-002: Edit Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-002
    
    User edits an existing architecture item through the UI.
    """
    # Navigate to System Architecture page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=System Architecture")
    page.wait_for_load_state("networkidle")
    
    # Click Edit on first item
    page.click("button[aria-label='Edit']:first")
    
    # Modify content
    content_area = page.locator("textarea[aria-label='Content']")
    content_area.fill("Updated architecture component description")
    
    # Save
    page.click("button:has-text('Save')")
    page.wait_for_load_state("networkidle")
    
    # Verify updated content
    expect(page.locator("text=Updated architecture component")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_005_003_approve_architecture_item(page: Page, streamlit_app):
    """
    TC-CRS-005-003: Approve Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-003
    
    User approves an architecture item through workflow.
    """
    # Navigate to System Architecture page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=System Architecture")
    page.wait_for_load_state("networkidle")
    
    # Click on first item to view details
    page.click("text=SYSARCH-001")
    page.wait_for_load_state("networkidle")
    
    # Verify current status
    expect(page.locator("text=draft")).to_be_visible()
    
    # Click Approve button
    page.click("button:has-text('Approve')")
    page.wait_for_load_state("networkidle")
    
    # Verify status changed to approved
    expect(page.locator("text=approved")).to_be_visible()
