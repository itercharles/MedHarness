"""
Pytest configuration for CRS browser tests.

Manages test data isolation and Playwright setup.
Uses static baseline DHF for stable, repeatable tests.
"""

import pytest
import shutil
import tempfile
import yaml
import subprocess
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def test_dhf_root():
    """
    Create isolated test DHF directory from static baseline.
    
    This ensures tests don't modify production DHF data and remain
    stable even when production DHF changes.
    """
    # Create temp directory
    test_dir = Path(tempfile.mkdtemp(prefix="test_dhf_"))
    
    print(f"\n🔧 Creating test DHF directory: {test_dir}")
    
    try:
        # Source DHF from static baseline (not production DHF)
        # This ensures tests are stable and don't break when production DHF changes
        # Baseline is shared across all test suites in tests/fixtures/
        baseline_dhf = Path(__file__).parent.parent / "fixtures" / "baseline_dhf"
        
        if not baseline_dhf.exists():
            # Fallback to production DHF in CI
            production_dhf = Path(__file__).parent.parent.parent / "DHF"
            print(f"\n⚠️  Baseline DHF not found, using production DHF: {production_dhf}")
            yield production_dhf
            return

        
        # Create directory structure
        (test_dir / "items").mkdir(parents=True)
        (test_dir / "config").mkdir(parents=True)
        (test_dir / "documents" / "specifications" / "templates").mkdir(parents=True)
        (test_dir / "governance").mkdir(parents=True)
        
        # Copy project configuration from baseline
        config_src = baseline_dhf / "config" / "project_config.yaml"
        config_dst = test_dir / "config" / "project_config.yaml"
        
        # Load and verify config paths are relative
        with open(config_src) as f:
            config = yaml.safe_load(f)
        
        # Verify directory paths in config are relative
        for doc_type in config.get('doc_types', []):
            directory = doc_type.get('directory', '')
            # Paths should be relative (e.g., "01_req_crs" not "/absolute/path")
            assert not directory.startswith('/'), \
                f"Config has absolute path: {directory}. Should be relative."
        
        # Copy config
        shutil.copy(config_src, config_dst)
        
        # Copy templates from baseline
        templates_src = baseline_dhf / "documents" / "specifications" / "templates"
        templates_dst = test_dir / "documents" / "specifications" / "templates"
        if templates_src.exists():
            shutil.copytree(templates_src, templates_dst, dirs_exist_ok=True)
        
        # Copy governance from baseline
        governance_src = baseline_dhf / "governance"
        governance_dst = test_dir / "governance"
        if governance_src.exists():
            shutil.copytree(governance_src, governance_dst, dirs_exist_ok=True)
        
        # Copy ALL items from baseline DHF (full copy for complete UI rendering)
        items_src = baseline_dhf / "items"
        items_dst = test_dir / "items"
        
        if items_src.exists():
            # Copy entire items directory from baseline
            shutil.copytree(items_src, items_dst, dirs_exist_ok=True)
            
            # Count directories
            item_dirs = [d for d in items_dst.iterdir() if d.is_dir()]
            print(f"✅ Test DHF created from baseline: {len(item_dirs)} item directories")
        
        yield test_dir
        
    finally:
        # Cleanup after all tests
        print(f"\n🧹 Cleaning up test DHF directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


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


@pytest.fixture(scope="function")
def page(browser):
    """Create new page for each test"""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='en-US'
    )
    page = context.new_page()
    
    # Set longer timeout for Streamlit
    page.set_default_timeout(30000)  # 30 seconds
    
    yield page
    
    # Cleanup
    context.close()


@pytest.fixture(scope="session")
def streamlit_app(test_dhf_root):
    """
    Start Streamlit app with isolated test DHF directory.
    
    This ensures tests don't modify production DHF data.
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    # Set environment variable
    env = os.environ.copy()
    env['DHF_ROOT'] = str(test_dhf_root)
    env['PYTHONPATH'] = f"{project_root}/src:{env.get('PYTHONPATH', '')}"
    
    print(f"\n🚀 Starting Streamlit with test DHF: {test_dhf_root}")
    
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
    print("⏳ Waiting for Streamlit to start...")
    time.sleep(15)
    
    # Verify it's running
    import requests
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        print(f"✅ Streamlit is running (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Streamlit failed to start: {e}")
        process.kill()
        raise
    
    yield "http://localhost:8501"
    
    # Cleanup: kill Streamlit
    print("\n🛑 Stopping Streamlit...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("✅ Streamlit stopped")


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "browser: mark test as browser-based (requires Streamlit running)"
    )
