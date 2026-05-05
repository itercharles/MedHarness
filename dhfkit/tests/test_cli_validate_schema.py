"""Tests for CLI command: validate schema"""
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner


from dhfkit.cli import main


def test_validate_schema_passes_on_clean_dhf(populated_dhf):
    """validate schema exits 0 on a valid test DHF."""
    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'validate', 'schema'])
    assert result.exit_code == 0


def test_validate_schema_fails_on_invalid_item(populated_dhf):
    """validate schema exits 1 when a YAML file contains unknown fields."""
    bad_file = populated_dhf / 'items' / '02_sys' / 'SYS-001.yaml'
    content = bad_file.read_text(encoding="utf-8")
    bad_file.write_text(content + "\nunknown_field_xyz: should_not_be_here\n", encoding="utf-8")

    result = CliRunner().invoke(main, ['--dhf', str(populated_dhf), 'validate', 'schema'])
    assert result.exit_code == 1
