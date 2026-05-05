"""Tests for CLI command: item list [--type CODE]"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


from dhfkit.cli import main


def _parse_lines(output: str) -> list[dict]:
    """Parse newline-delimited JSON output, skipping non-JSON lines."""
    results = []
    for line in output.strip().splitlines():
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return results


def test_item_list_returns_all_items(populated_dhf):
    """item list returns all items as newline-delimited JSON."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert len(items) > 0


def test_item_list_filter_by_type(populated_dhf):
    """item list --type SYS returns only SYS items."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list', '--type', 'SYS'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert len(items) > 0
    for item in items:
        assert item['id'].startswith('SYS-'), f"Expected SYS- prefix, got {item['id']}"


def test_item_list_filter_unknown_type_returns_empty(populated_dhf):
    """item list --type UNKNOWN returns no items (empty output, exit 0)."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'item', 'list', '--type', 'UNKNOWN'])
    assert result.exit_code == 0
    items = _parse_lines(result.output)
    assert items == []
