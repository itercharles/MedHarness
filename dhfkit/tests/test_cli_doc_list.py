"""Tests for CLI command: doc list"""
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



def test_doc_list_exits_0(populated_dhf):
    """doc list exits with code 0."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'list'])
    assert result.exit_code == 0


def test_doc_list_returns_doc_types_key(populated_dhf):
    """doc list returns JSON with a 'doc_types' key."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'list'])
    data = _parse_json(result.output)
    assert 'doc_types' in data
    assert isinstance(data['doc_types'], list)
