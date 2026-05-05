"""Tests for CLI command: item update <item_id> --data JSON"""
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



def test_item_update_changes_field(populated_dhf):
    """item update modifies a field and returns the updated item."""
    data = json.dumps({'title': 'Updated title'})
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'update', 'SYS-001',
        '--data', data,
    ])
    assert result.exit_code == 0
    updated = _parse_json(result.output)
    assert updated['title'] == 'Updated title'


def test_item_update_persists_change(populated_dhf):
    """Updated field is visible when item get is called afterwards."""
    data = json.dumps({'title': 'Persisted update'})
    CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'update', 'SYS-001', '--data', data,
    ])
    get_result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', 'SYS-001'])
    assert _parse_json(get_result.output)['title'] == 'Persisted update'


def test_item_update_not_found_exits_1(populated_dhf):
    """item update exits with code 1 when item does not exist."""
    data = json.dumps({'title': 'Ghost'})
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'update', 'FAKE-999',
        '--data', data,
    ])
    assert result.exit_code == 1


def test_item_update_invalid_json_exits_1(populated_dhf):
    """item update with malformed --data JSON exits with code 1."""
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'update', 'SYS-001',
        '--data', 'not-json',
    ])
    assert result.exit_code == 1
