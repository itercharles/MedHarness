"""A doc type's code and its ID prefix are two things; nothing may assume `<CODE>-`.

The loader, the store and the lifecycle each read the type from the first segment
of an ID, so a type `HWREQ` with prefix `HWR-` could not be loaded at all: its items
were "Unknown doc type 'HWR'".
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main as cli
from medharness.scaffold import replace_placeholders, scaffold_dhf

TYPE = """code: HWREQ
name: Hardware Requirement
prefix: HWR-
directory: 20_hwr
properties:
- id
- name: title
  format: short_text
  label: Title
"""


def _project(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Prefix")
    dhf = tmp_path / "DHF"
    (dhf / "config" / "doc_types").mkdir(exist_ok=True)
    (dhf / "config" / "doc_types" / "hwr.yaml").write_text(TYPE)
    (dhf / "items" / "20_hwr").mkdir()
    (dhf / "items" / "20_hwr" / "HWR-001.yaml").write_text("id: HWR-001\ntitle: Existing\n")
    return dhf


def test_items_of_a_type_whose_code_differs_from_its_prefix_load_and_can_be_created(tmp_path: Path) -> None:
    dhf = _project(tmp_path)
    runner = CliRunner()

    listed = runner.invoke(cli, ["--dhf", str(dhf), "item", "list", "--type", "HWREQ"])
    assert listed.exit_code == 0, listed.output
    assert "HWR-001" in listed.stdout

    created = runner.invoke(cli, ["--dhf", str(dhf), "item", "create", "--type", "HWREQ",
                                  "--data", json.dumps({"title": "New"})])
    assert created.exit_code == 0, created.output
    assert json.loads(created.stdout)["id"] == "HWR-002"
