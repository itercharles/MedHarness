"""Tests for CLI command: doc generate <doc_type>"""
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



def _get_available_doc_types(populated_dhf) -> list[str]:
    """Helper: return available doc types from the test DHF."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'list'])
    return _parse_json(result.output).get('doc_types', [])


def test_doc_generate_single_type(populated_dhf):
    """doc generate <type> exits 0 and returns JSON with output_path."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")

    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', 'generate', doc_types[0],
    ])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert 'output_path' in data


def test_doc_generate_all(populated_dhf):
    """doc generate ALL exits 0."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")

    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'generate', 'ALL'])
    assert result.exit_code == 0


def test_doc_generate_unknown_type_exits_1(populated_dhf):
    """doc generate with an unknown type exits 1."""
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', 'generate', 'NONEXISTENT_TYPE_XYZ',
    ])
    assert result.exit_code == 1
