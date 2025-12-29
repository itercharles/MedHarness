"""
Pytest configuration for SYS browser tests.

Manages test data isolation and Playwright setup.
Uses shared test data fixtures from tests/fixtures/test_data.py
"""

import pytest
import shutil
import subprocess
import time
import os
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.fixtures.test_data import create_test_dhf, populate_test_dhf


@pytest.fixture(scope="session")
def test_dhf_root():
    """Create isolated test DHF directory with proper configuration."""
    test_dir = create_test_dhf()
    yield test_dir
    
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"\n[CLEANUP] Cleaned up test DHF: {test_dir}")


@pytest.fixture(scope="session")
def populate_test_dhf_fixture(test_dhf_root):
    """Populate test DHF with minimal dataset for browser tests."""
    return populate_test_dhf(test_dhf_root)


@pytest.fixture(scope="session")
def browser():
    """Launch headless browser for tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']  # For CI/CD
        )
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def context(browser):
    """Create browser context"""
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    yield context
    context.close()


@pytest.fixture
def page(context):
    """Create new page for each test"""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def streamlit_app(test_dhf_root, populate_test_dhf_fixture):
    """
    Start Streamlit app with isolated test DHF directory.
    
    In CI, uses existing Streamlit instance. Locally, starts new instance.
    """
    # Check if Streamlit is already running (CI environment)
    try:
        response = requests.get("http://localhost:8501", timeout=2)
        if response.status_code == 200:
            print("\n[OK] Streamlit already running (CI), using existing instance")
            yield "http://localhost:8501"
            return
    except requests.exceptions.RequestException:
        pass  # Not running, will start it
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    # Set environment variable
    env = os.environ.copy()
    env['DHF_ROOT'] = str(test_dhf_root)
    env['PYTHONPATH'] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"
    
    print(f"\n[SETUP] Starting Streamlit with test DHF: {test_dhf_root}")
    
    # Start Streamlit in background
    process = subprocess.Popen(
        [
            "streamlit",
            "run",
            str(project_root / "src" / "app.py"),
            "--server.port", "8501",
            "--server.headless", "true"
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(project_root)
    )
    
    # Wait for Streamlit to start
    print("[SETUP] Waiting for Streamlit to start...")
    time.sleep(15)
    
    # Verify it's running
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        print(f"[OK] Streamlit is running (status: {response.status_code})")
    except Exception as e:
        print(f"[WARN] Streamlit failed to start: {e}")
    
    yield "http://localhost:8501"
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)
    print("\n[CLEANUP] Streamlit stopped")
