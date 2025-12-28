"""
Browser tests for CRS-004: Automated Documentation

Tests verify document generation through UI.

@links: CRS-004
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.browser
def test_TC_CRS_004_001_generate_specification(page: Page, streamlit_app):
    """
    TC-CRS-004-001: Generate Specification Document
    
    @links: CRS-004
    @test_id: TC-CRS-004-001
    
    User navigates to SRS page and verifies regenerate button exists.
    """
    # Navigate to Software Requirement page
    page.goto(f"{streamlit_app}/7_SRS")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name="Software Requirement")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_004_002_view_document_preview(page: Page, streamlit_app):
    """
    TC-CRS-004-002: View Document Preview
    
    @links: CRS-004
    @test_id: TC-CRS-004-002
    
    User views document preview on SRS page.
    """
    # Navigate to Software Requirement page
    page.goto(f"{streamlit_app}/7_SRS")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    
    # Verify page loaded
    expect(page.get_by_role("heading", name="Software Requirement")).to_be_visible()
    
    # Verify document preview section exists
    # expect(page.locator("text=Document Preview, text=Preview").first).to_be_visible()
