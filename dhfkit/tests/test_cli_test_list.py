"""Tests for CLI command: test list [--status STATUS]"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


from dhfkit.cli import main


@pytest.fixture
def dhf_with_results(populated_dhf):
    """Populate ResultStore with two test records."""
    from dhfkit.result_store import ResultStore
    store = ResultStore(populated_dhf)
    store.record_execution(
        tc_id="TC-SYS-001", testing_status="PASS",
        tester="ci", run_id="1", run_url="http://example.com/runs/1",
        commit_sha="abc123", links=["SYS-001"], title="Test case 1",
    )
    store.record_execution(
        tc_id="TC-SYS-002", testing_status="FAIL",
        tester="ci", run_id="1", run_url="http://example.com/runs/1",
        commit_sha="abc123", links=["SYS-002"], title="Test case 2",
    )
    return populated_dhf


def _parse_lines(output: str) -> list[dict]:
    results = []
    for line in output.strip().splitlines():
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return results


def test_test_list_returns_all_records(dhf_with_results):
    """test list without filter returns all stored records."""
    result = CliRunner().invoke(main, ['--dhf', str(dhf_with_results), 'test', 'list'])
    assert result.exit_code == 0
    records = _parse_lines(result.output)
    assert len(records) == 2


def test_test_list_filter_by_status_pass(dhf_with_results):
    """test list --status PASS returns only PASS records."""
    result = CliRunner().invoke(main, [
        '--dhf', str(dhf_with_results), 'test', 'list', '--status', 'PASS',
    ])
    assert result.exit_code == 0
    records = _parse_lines(result.output)
    assert len(records) == 1
    assert records[0]['testing_status'] == 'PASS'


def test_test_list_filter_by_status_fail(dhf_with_results):
    """test list --status FAIL returns only FAIL records."""
    result = CliRunner().invoke(main, [
        '--dhf', str(dhf_with_results), 'test', 'list', '--status', 'FAIL',
    ])
    assert result.exit_code == 0
    records = _parse_lines(result.output)
    assert len(records) == 1
    assert records[0]['testing_status'] == 'FAIL'


def test_test_list_empty_store_exits_0(populated_dhf):
    """test list on DHF with no results exits 0 and returns no records."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'test', 'list'])
    assert result.exit_code == 0
    records = _parse_lines(result.output)
    assert records == []
