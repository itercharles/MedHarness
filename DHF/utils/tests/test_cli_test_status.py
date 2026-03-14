"""Tests for CLI command: test status <tc_id>"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "DHF"))

from utils.cli import main


@pytest.fixture
def dhf_with_results(populated_dhf):
    """Populate ResultStore with two test records."""
    from utils.result_store import ResultStore
    store = ResultStore(populated_dhf)
    store.record_execution(
        tc_id="TC-SYS-001",
        testing_status="PASS",
        tester="ci",
        run_id="1",
        run_url="http://example.com/runs/1",
        commit_sha="abc123",
        links=["SYS-001"],
        title="Test case 1",
    )
    return populated_dhf


def test_test_status_existing_record(dhf_with_results):
    """test status returns JSON record for a known TC ID."""
    result = CliRunner().invoke(main, [
        '--dhf', str(dhf_with_results), 'test', 'status', 'TC-SYS-001',
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data['testing_status'] == 'PASS'


def test_test_status_not_found_exits_1(dhf_with_results):
    """test status exits 1 when TC ID has no record."""
    result = CliRunner().invoke(main, [
        '--dhf', str(dhf_with_results), 'test', 'status', 'TC-FAKE-999',
    ])
    assert result.exit_code == 1
