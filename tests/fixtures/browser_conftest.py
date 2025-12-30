"""
Shared pytest configuration for browser tests (CRS and SYS).

Manages test data isolation and Playwright setup.
Uses shared test data fixtures from tests/fixtures/test_data.py
"""

import sys
import pytest
import shutil
import subprocess
import time
import os
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fixtures.test_data import create_test_dhf, populate_test_dhf

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
    
    Each test session gets its own Streamlit instance with test data.
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    
    # Backup existing app_config.yaml if it exists
    app_config_path = project_root / "app_config.yaml"
    backup_config_path = project_root / "app_config.yaml.backup"
    
    if app_config_path.exists():
        shutil.copy(app_config_path, backup_config_path)
        print(f"[SETUP] Backed up existing app_config.yaml")
    
    # Create test config file
    test_config_content = f"dhf_root: {test_dhf_root}\n"
    with open(app_config_path, 'w') as f:
        f.write(test_config_content)
    print(f"[SETUP] Wrote test config: {test_config_content.strip()}")
    print(f"[SETUP] Config file location: {app_config_path}")
    
    print(f"\n[SETUP] Starting Streamlit with test DHF: {test_dhf_root}")
    
    # Start Streamlit in background
    # Try venv streamlit first (local dev), fall back to system streamlit (CI)
    venv_streamlit = project_root / "venv" / "bin" / "streamlit"
    streamlit_cmd = str(venv_streamlit) if venv_streamlit.exists() else "streamlit"
    
    # Redirect stderr and stdout to temp files for debugging
    import tempfile
    stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_streamlit_stderr.log')
    stderr_path = stderr_file.name
    stderr_file.close()
    
    stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_streamlit_stdout.log')
    stdout_path = stdout_file.name
    stdout_file.close()
    
    app_path = str(project_root / "src" / "app.py")
    cmd = [
        streamlit_cmd,
        "run",
        app_path,
        "--server.port", "8501",
        "--server.headless", "true"
    ]
    print(f"[DEBUG] Streamlit command: {' '.join(cmd)}")
    print(f"[DEBUG] Working directory: {project_root}")
    print(f"[DEBUG] App file exists: {Path(app_path).exists()}")
    
    process = subprocess.Popen(
        cmd,
        stdout=open(stdout_path, 'w'),
        stderr=open(stderr_path, 'w'),
        cwd=str(project_root)
    )
    
    # Wait for Streamlit HTTP server to start
    # Note: The app won't actually render until a browser connects via WebSocket
    print("[SETUP] Waiting for Streamlit server to start...")
    max_retries = 30  # 30 seconds
    retry_count = 0
    server_ready = False
    
    while retry_count < max_retries and not server_ready:
        time.sleep(1)
        retry_count += 1
        
        # Check if process is still alive
        if process.poll() is not None:
            print(f"[ERROR] Streamlit process died with exit code {process.returncode}")
            try:
                with open(stderr_path, 'r') as f:
                    stderr_output = f.read()
                    if stderr_output:
                        print(f"[STDERR] Streamlit output:\n{stderr_output}")
            except:
                pass
            break
        
        # Just check if HTTP server is responding
        try:
            response = requests.get("http://localhost:8501", timeout=2)
            if response.status_code == 200:
                server_ready = True
                print(f"[OK] Streamlit server is ready (after {retry_count}s)")
        except Exception:
            if retry_count % 5 == 0:
                print(f"[WAIT] Waiting for Streamlit server... ({retry_count}s)")
    
    if not server_ready:
        print(f"[ERROR] Streamlit server failed to start after {max_retries}s")
        try:
            with open(stdout_path, 'r') as f:
                stdout_output = f.read()
                if stdout_output:
                    print(f"[STDOUT] Streamlit stdout:\n{stdout_output[-1000:]}")
        except Exception as e:
            print(f"[ERROR] Could not read stdout: {e}")
        try:
            with open(stderr_path, 'r') as f:
                stderr_output = f.read()
                if stderr_output:
                    print(f"[STDERR] Streamlit stderr:\n{stderr_output[-1000:]}")
        except Exception as e:
            print(f"[ERROR] Could not read stderr: {e}")
    else:
        # Server started successfully - check logs for any warnings/errors
        print("[DEBUG] Checking Streamlit logs...")
        try:
            with open(stdout_path, 'r') as f:
                stdout_output = f.read()
                if stdout_output:
                    print(f"[STDOUT] Last 500 chars:\n{stdout_output[-500:]}")
        except:
            pass
        try:
            with open(stderr_path, 'r') as f:
                stderr_output = f.read()
                if stderr_output:
                    print(f"[STDERR] Last 500 chars:\n{stderr_output[-500:]}")
        except:
            pass
    
    
    
    
    
    
    try:
        yield "http://localhost:8501"
    finally:
        # Cleanup - guaranteed to run even if test fails
        process.terminate()
        process.wait(timeout=5)
        
        # Clean up temp files
        try:
            if os.path.exists(stderr_path):
                os.unlink(stderr_path)
            if os.path.exists(stdout_path):
                os.unlink(stdout_path)
        except:
            pass
        
        # Restore original app_config.yaml
        if backup_config_path.exists():
            shutil.move(backup_config_path, app_config_path)
            print("[CLEANUP] Restored original app_config.yaml")
        else:
            # Remove test config if there was no original
            if app_config_path.exists():
                app_config_path.unlink()
                print("[CLEANUP] Removed test app_config.yaml")
        
        print("\n[CLEANUP] Streamlit stopped")
