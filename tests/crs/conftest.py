"""
Pytest configuration for CRS browser tests.
Imports shared fixtures from tests/fixtures/browser_conftest.py
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from tests.fixtures
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all fixtures from shared browser conftest
from fixtures.browser_conftest import *  # noqa: F401, F403
