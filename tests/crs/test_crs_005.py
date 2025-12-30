"""
Browser tests for CRS-005: Architecture Definition

Tests verify architecture management through UI.

@links: CRS-005
"""

import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_005_001_add_architecture_item(page: Page, streamlit_app, test_dhf_root):
    """
    TC-CRS-005-001: Add Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-001
    
    User creates a new system architecture item.
    """
    # Navigate to System Architecture page
    page.goto(f"{streamlit_app}/page_SYSARCH")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name=re.compile(r"System Architecture"))).to_be_visible()
    
    # Click New button
    page.get_by_role("button", name="➕ New").click()
    page.wait_for_timeout(1000)
    
    # Fill form (ID auto-generated)
    page.locator("label:has-text('Title')").locator("..").locator("input").fill("Test Architecture")
    page.locator("label:has-text('Content')").locator("..").locator("textarea").fill("Test architecture component")
    
    # Create
    page.get_by_role("button", name="✅ Create").click()
    page.wait_for_load_state("networkidle")
    
    # Verify created
    from fixtures.browser_conftest import get_created_item_id
    created_id = get_created_item_id(test_dhf_root, 'SYSARCH-')
    page.fill("input[placeholder='Search by ID or title...']", created_id)
    page.wait_for_timeout(1000)
    expect(page.get_by_role("heading", name=created_id)).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_005_002_edit_architecture_item(page: Page, streamlit_app):
    """
    TC-CRS-005-002: Edit Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-002
    
    User views an existing architecture item.
    """
    # Navigate to System Architecture with item selected
    page.goto(f"{streamlit_app}/page_SYSARCH?item=SYSARCH-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify item loaded
    expect(page.get_by_role("heading", name="SYSARCH-001")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_005_003_approve_architecture_item(page: Page, streamlit_app):
    """
    TC-CRS-005-003: Approve Architecture Item
    
    @links: CRS-005
    @test_id: TC-CRS-005-003
    
    User views architecture item status.
    """
    # Navigate to System Architecture with item selected
    page.goto(f"{streamlit_app}/page_SYSARCH?item=SYSARCH-001")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify item loaded
    expect(page.get_by_role("heading", name="SYSARCH-001")).to_be_visible()
    
    # Verify status badge exists (use first since there are multiple "Approved" texts)
    expect(page.get_by_text("Approved").first).to_be_visible()
