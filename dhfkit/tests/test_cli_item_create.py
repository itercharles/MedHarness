"""Tests for CLI command: item create --type CODE --data JSON"""
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



def test_item_create_sys_returns_created_item(populated_dhf):
    """item create --type SYS outputs the created item as JSON."""
    data = json.dumps({'title': 'New system req', 'content': 'Shall do X', 'category': 'Functional'})
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'create',
        '--type', 'SYS', '--data', data,
    ])
    assert result.exit_code == 0
    created = _parse_json(result.output)
    assert created['id'].startswith('SYS-')
    assert created['title'] == 'New system req'


def test_item_create_cr_gets_draft_status(populated_dhf):
    """item create --type CR auto-assigns draft status."""
    data = json.dumps({'title': 'Fix bug', 'description': 'desc', 'justification': 'j'})
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'create',
        '--type', 'CR', '--data', data,
    ])
    assert result.exit_code == 0
    created = _parse_json(result.output)
    assert created['status'] == 'draft'


def test_item_create_invalid_json_exits_1(populated_dhf):
    """item create with malformed --data JSON exits with code 1."""
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'create',
        '--type', 'SYS', '--data', '{not valid json',
    ])
    assert result.exit_code == 1


def test_item_create_ignores_supplied_id(populated_dhf):
    """item create ignores any id field in --data and auto-generates one (CR-006)."""
    data = json.dumps({'id': 'SYS-999', 'title': 'Should ignore ID', 'content': 'x', 'category': 'Functional'})
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'create',
        '--type', 'SYS', '--data', data,
    ])
    assert result.exit_code == 0
    created = _parse_json(result.output)
    assert created['id'] != 'SYS-999'
    assert created['id'].startswith('SYS-')


def test_item_create_persists_item(populated_dhf):
    """Created item can be retrieved by item get."""
    data = json.dumps({'title': 'Persist test', 'content': 'Content', 'category': 'Functional'})
    create_result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'item', 'create',
        '--type', 'SYS', '--data', data,
    ])
    assert create_result.exit_code == 0
    created_id = _parse_json(create_result.output)['id']

    get_result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'get', created_id])
    assert get_result.exit_code == 0
    assert _parse_json(get_result.output)['id'] == created_id
