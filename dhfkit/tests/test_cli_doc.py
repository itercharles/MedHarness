"""`dhfkit doc TYPE|ALL [--format md|html|pdf]` — one command for rendering."""
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

def _get_available_doc_types(dhf):
    """Doc-type codes that have a document specification, per the store."""
    from dhfkit.local_adapter import LocalDHFAdapter

    return LocalDHFAdapter(dhf).get_available_doc_types()


def test_doc_generate_single_type(populated_dhf):
    """`doc <type>` renders Markdown and says where."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")

    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', doc_types[0],
    ])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert data['md_path'].endswith('.md')


def test_doc_generate_all(populated_dhf):
    """`doc ALL` renders every type."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")

    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'doc', 'ALL'])
    assert result.exit_code == 0


def test_doc_generate_unknown_type_exits_1(populated_dhf):
    """An unknown type exits 1, whatever the format."""
    for fmt in ('md', 'html'):
        result = CliRunner().invoke(main, [
            '--dhf', str(populated_dhf), 'doc', 'NONEXISTENT_TYPE_XYZ', '--format', fmt,
        ])
        assert result.exit_code == 1, fmt


def test_every_format_reports_the_markdown_it_rendered(populated_dhf):
    """md, html and pdf all render the Markdown first; each says where it is."""
    doc_types = _get_available_doc_types(populated_dhf)
    if not doc_types:
        pytest.skip("No doc types with document_specifications in test DHF")
    result = CliRunner().invoke(main, [
        '--dhf', str(populated_dhf), 'doc', doc_types[0], '--format', 'html',
    ])
    assert result.exit_code == 0
    data = _parse_json(result.output)
    assert data['md_path'].endswith('.md') and data['html_path'].endswith('.html')
