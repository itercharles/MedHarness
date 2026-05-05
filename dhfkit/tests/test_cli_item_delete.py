"""Tests for CLI command: item delete <item_id>"""
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



def test_item_delete_existing_item(populated_dhf):
    """item delete removes the item and outputs confirmation JSON."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'delete', 'SYS-002'])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert data['deleted'] == 'SYS-002'


def test_item_delete_item_no_longer_retrievable(populated_dhf):
    """Deleted item cannot be retrieved by item get."""
    CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'delete', 'SRS-001'])
    get_result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'SRS-001'])
    assert get_result.exit_code == 1


def test_item_delete_not_found_exits_1(populated_dhf):
    """item delete exits with code 1 when item does not exist."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'delete', 'FAKE-999'])
    assert result.exit_code == 1
