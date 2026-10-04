"""A project's own types, link fields and chains reach the AI stage and its checks.

`build plan` was told a fixed V-model — a hard-coded link table in its prompt — and
checked its output against a fixed `CRS → SYS → SRS/SYSARCH → SWDD` cascade, so a
project with another structure was described to the model wrongly and held to
a cascade it did not have. `item get` also left a custom link field out of
`all_linked_uids`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from medharness.cli import main
from medharness.services.design_validation import _validate_cascade_completeness, cascade_children
from medharness.scaffold import replace_placeholders, scaffold_dhf


def _doc_type(code: str, link: str | None = None, target: str | None = None) -> dict:
    properties = ["id", {"name": "title", "format": "short_text", "label": "Title"},
                  {"name": "content", "format": "long_text", "label": "Content"}]
    if link:
        properties.append({"name": link, "format": "relationship", "label": link.title(),
                           "description": f"{code} {link} {target}", "target_types": [target]})
    return {"code": code, "name": f"{code} item", "prefix": f"{code}-", "directory": code.lower(), "properties": properties}


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """The starter DHF plus hardware requirements that refine SYS and are tested by TST."""
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Hw")
    dhf = tmp_path / "DHF"
    config = dhf / "config"
    (config / "doc_types").mkdir(exist_ok=True)
    (config / "doc_types" / "hwr.yaml").write_text(yaml.safe_dump(_doc_type("HWR", "refines", "SYS")))
    (config / "doc_types" / "tst.yaml").write_text(yaml.safe_dump(_doc_type("TST", "exercises", "HWR")))
    (config / "global.yaml").write_text((config / "global.yaml").read_text() + """
traceability_matrices:
- name: Hardware chain
  description: SYS to HWR to TST
  path: [SYS, HWR, TST]
""")
    for code, link, target in (("HWR", "refines", "SYS-001"), ("TST", "exercises", "HWR-001")):
        folder = dhf / "items" / code.lower()
        folder.mkdir(exist_ok=True)
        (folder / f"{code}-001.yaml").write_text(yaml.safe_dump({"id": f"{code}-001", "title": code, "content": "c", link: [target]}))
    return dhf


def _store_config(dhf: Path):
    from dhfkit.store import open_store

    return open_store(dhf).config


def test_the_cascade_is_the_projects_chain(dhf: Path) -> None:
    assert cascade_children(_store_config(dhf)) == {"HWR": ["TST"]}


def test_a_created_item_without_a_child_in_the_projects_chain_is_flagged(dhf: Path) -> None:
    by_id = {"HWR-002": {"id": "HWR-002", "refines": ["SYS-001"]}}
    errors = _validate_cascade_completeness(["HWR-002"], by_id, _store_config(dhf))
    assert [e["field"] for e in errors] == ["cascade.HWR-002"]
    assert "TST" in errors[0]["issue"]


def test_the_child_counts_through_its_own_declared_field(dhf: Path) -> None:
    by_id = {"HWR-002": {"id": "HWR-002"}, "TST-002": {"id": "TST-002", "exercises": ["HWR-002"]}}
    assert _validate_cascade_completeness(["HWR-002"], by_id, _store_config(dhf)) == []


def test_the_standard_chain_is_no_longer_assumed(dhf: Path) -> None:
    """With this project's matrix, a new SRS has no required child."""
    by_id = {"SRS-002": {"id": "SRS-002"}}
    assert _validate_cascade_completeness(["SRS-002"], by_id, _store_config(dhf)) == []


def test_the_plan_prompt_describes_the_projects_links_and_chains(dhf: Path) -> None:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "build", "plan", "--cr", "CR-001", "--prompt"])
    assert result.exit_code == 0, result.stderr
    assert "| HWR | `refines` | SYS | HWR refines SYS |" in result.stdout
    assert "| TST | `exercises` | HWR | TST exercises HWR |" in result.stdout
    assert "- SYS → HWR → TST" in result.stdout


def test_a_custom_link_field_is_among_the_linked_ids(dhf: Path) -> None:
    result = CliRunner().invoke(main, ["--dhf", str(dhf), "item", "get", "HWR-001"])
    assert json.loads(result.stdout)["all_linked_uids"] == ["SYS-001"]


def test_the_standard_design_roles_are_described_only_to_a_project_that_has_those_types() -> None:
    from medharness.services.prompt_assembly import _link_model

    bare = {"types": [{"code": "HWR", "links": []}], "chains": []}
    standard = {"types": [{"code": c, "links": []} for c in ("SYSARCH", "MODULE", "SWDD")], "chains": []}
    assert "Design layer roles" not in _link_model(bare)
    assert "Design layer roles" in _link_model(standard)
