"""
Pytest configuration for SYS browser tests.

This module provides fixtures for running browser tests against
System Requirements in an isolated test environment.
"""

import pytest
import subprocess
import time
import os
import tempfile
import shutil
import yaml
import requests
from pathlib import Path
import requests


@pytest.fixture(scope="session")
def test_dhf_root():
    """
    Create isolated test DHF directory from baseline.
    
    This fixture copies the baseline DHF to a temporary directory,
    ensuring tests don't modify the baseline or production DHF.
    Tests are stable even when production DHF changes.
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
        
        # Copy governance files
        gov_src = baseline_dhf / "governance"
        if gov_src.exists():
            for file in gov_src.glob("*.yaml"):
                shutil.copy(file, test_dir / "governance" / file.name)
        
        # Copy all items from baseline
        items_src = baseline_dhf / "items"
        items_dst = test_dir / "items"
        
        if items_src.exists():
            shutil.copytree(items_src, items_dst, dirs_exist_ok=True)
        
        # Count items for verification
        item_count = len(list(items_dst.glob("*")))
        print(f"✅ Test DHF created from baseline: {item_count} item directories")
        
        yield test_dir
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up test DHF directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def streamlit_app(test_dhf_root):
    """
    Start Streamlit app with test DHF for browser testing.
    
    This fixture starts a Streamlit server pointing to the isolated
    test DHF directory, ensuring tests don't affect production data.
    """
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
    max_retries = 30
    retry_delay = 1
    
    print("⏳ Waiting for Streamlit to start...")
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8501")
            if response.status_code == 200:
                print("✅ Streamlit is running (status: 200)")
                break
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                time.sleep(retry_delay)
            else:
                process.kill()
                raise RuntimeError(f"Streamlit failed to start after {max_retries} seconds")
    
    yield "http://localhost:8501"
    
    # Cleanup
    print("\n🛑 Stopping Streamlit...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("✅ Streamlit stopped")


@pytest.fixture(scope="function")
def page(playwright):
    """Create a new browser page for each test."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    yield page
    
    page.close()
    context.close()
    browser.close()
