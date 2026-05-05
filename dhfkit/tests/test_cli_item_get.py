"""Tests for CLI command: item get <item_id>"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


from dhfkit.cli import main


def _parse_json(output: str):
    """Return the first JSON line from CLI output, skipping warning/status lines."""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('{') or line.startswith('['):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")


def test_item_get_existing_item(populated_dhf):
    """item get returns JSON for a known item."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'SYS-001'])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert data['id'] == 'SYS-001'


def test_item_get_includes_title(populated_dhf):
    """item get output includes the item title."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'CRS-001'])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert 'title' in data


def test_item_get_not_found_exits_1(populated_dhf):
    """item get exits with code 1 when item does not exist."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'FAKE-999'])
    assert result.exit_code == 1


def test_item_get_not_found_prints_error(populated_dhf):
    """item get prints an error message when item not found."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'FAKE-999'])
    assert 'FAKE-999' in result.output or 'not found' in result.output.lower()
