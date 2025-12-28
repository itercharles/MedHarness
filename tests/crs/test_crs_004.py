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
    
    User generates a specification document and downloads PDF.
    """
    # Navigate to Documents page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=Documents")
    page.wait_for_load_state("networkidle")
    
    # Select Software Requirements Specification
    page.select_option("select[aria-label='Document Type']", "SRS")
    
    # Click Generate Document
    page.click("button:has-text('Generate Document')")
    
    # Wait for generation (progress indicator)
    page.wait_for_selector("text=Generating...", state="visible", timeout=5000)
    page.wait_for_selector("text=Generating...", state="hidden", timeout=30000)
    
    # Verify download link appears
    expect(page.locator("a:has-text('Download PDF')")).to_be_visible()


@pytest.mark.browser
def test_TC_CRS_004_002_view_document_preview(page: Page, streamlit_app):
    """
    TC-CRS-004-002: View Document Preview
    
    @links: CRS-004
    @test_id: TC-CRS-004-002
    
    User views markdown preview of generated document.
    """
    # Navigate to Documents page
    page.goto(streamlit_app)
    page.wait_for_selector("[data-testid='stApp']")
    page.click("text=Documents")
    page.wait_for_load_state("networkidle")
    
    # Click View on existing SRS document
    page.click("button:has-text('View'):first")
    page.wait_for_load_state("networkidle")
    
    # Verify markdown preview displays
    expect(page.locator(".markdown-body, [data-testid='stMarkdown']")).to_be_visible()
    
    # Verify all SRS items are included
    expect(page.locator("text=SRS-001")).to_be_visible()
    
    # Verify table of contents present
    expect(page.locator("text=Table of Contents, text=Contents")).to_be_visible()
