"""Tests for CLI command: doc export <doc_type>"""
import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

weasyprint = pytest.importorskip("weasyprint", reason="weasyprint not installed; skipping PDF export tests")


from dhfkit.cli import main

def _parse_json(output: str):
    """Return the first JSON line from CLI output, skipping warning/status lines."""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('{') or line.startswith('['):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output!r}")



def _get_available_doc_types(populated_dhf) -> list[str]:
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'list'])
    return _parse_json(result.output).get('doc_types', [])


def test_doc_export_single_type(populated_dhf):
    """doc export <type> exits 0 and returns JSON with pdf_path."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")

    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', 'export', doc_types[0],
    ])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert 'pdf_path' in data


def test_doc_export_unknown_type_exits_1(populated_dhf):
    """doc export with an unknown type exits 1."""
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', 'export', 'NONEXISTENT_TYPE_XYZ',
    ])
    assert result.exit_code == 1
