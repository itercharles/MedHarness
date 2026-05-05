"""Tests for CLI command: config doc-types"""
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



def test_config_doc_types_exits_0(populated_dhf):
    """config doc-types exits with code 0."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'config', 'doc-types'])
    assert result.exit_code == 0


def test_config_doc_types_returns_json_list(populated_dhf):
    """config doc-types returns a JSON array of doc type objects."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'config', 'doc-types'])
    doc_types = _parse_json(result.output)
    assert isinstance(doc_types, list)
    assert len(doc_types) > 0


def test_config_doc_types_each_has_code_and_prefix(populated_dhf):
    """Each doc type entry contains code and prefix fields."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'config', 'doc-types'])
    doc_types = _parse_json(result.output)
    for dt in doc_types:
        assert 'code' in dt, f"Missing 'code' in {dt}"
        assert 'prefix' in dt, f"Missing 'prefix' in {dt}"
