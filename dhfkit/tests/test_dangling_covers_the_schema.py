"""Every relationship field the schema declares must have dangling detection.

Two hand-written lists decided this between them — `_TRACEABILITY_LINK_FIELDS`
in the adapter and `_LINK_FIELDS` in the checker — and they disagreed. Of the
nine relationship fields in the shipped schema, four were checked.

`affected_risk_items` is the sharpest case: the checker listed it, so someone
meant it to be checked, and the adapter never supplied it. A link the checker
looks at but the loader does not pass is a check that silently does nothing.

Doc types are project-owned. Deriving the field set from the schema means a
project that adds a relationship field gets it checked without editing this
package — and this test covers fields that do not exist yet.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from dhfkit.local_adapter import LocalDHFAdapter
from dhfkit.models.config import ProjectConfig
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "config" / "doc_types"


def _relationship_fields() -> list[tuple[str, str]]:
    """(field, first doc-type code that declares it) straight from the templates."""
    found: dict[str, str] = {}
    for path in sorted(TEMPLATES.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        for prop in doc.get("properties", []):
            if isinstance(prop, dict) and prop.get("format") == "relationship":
                found.setdefault(prop["name"], doc["code"])
    return sorted(found.items())


FIELDS = _relationship_fields()


def test_the_scan_found_fields() -> None:
    assert len(FIELDS) >= 8, FIELDS


@pytest.mark.parametrize("field,code", FIELDS, ids=[f for f, _ in FIELDS])
def test_a_dangling_link_is_detected(field: str, code: str, tmp_path: Path) -> None:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Dangling")
    dhf = tmp_path / "DHF"

    target = next(((dhf / "items").rglob(f"{code}-*.yaml")), None)
    if target is None:
        pytest.skip(f"the scaffold has no {code} item to hang a link on")

    data = yaml.safe_load(target.read_text())
    data[field] = ["ZZZ-999"]
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    result = LocalDHFAdapter(dhf).validate_traceability()
    hits = [d for d in result.get("dangling", []) if d.get("field") == field]
    assert hits, (
        f"a dangling {field} link was not reported. The field is declared "
        f"`format: relationship` on {code}, so a target that does not exist is "
        f"a broken reference like any other."
    )
    assert hits[0]["target"] == "ZZZ-999"


class TestTheFieldSetComesFromTheSchema:
    def test_config_reports_every_declared_relationship(self, tmp_path: Path) -> None:
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Derived")
        config = ProjectConfig.load(tmp_path / "DHF" / "config")
        assert config.relationship_fields() == {f for f, _ in FIELDS}

    def test_a_project_defined_field_is_picked_up(self, tmp_path: Path) -> None:
        """The point of deriving: a field this package has never heard of."""
        _scaffold_dhf(tmp_path)
        _replace_placeholders(tmp_path, "Custom")
        dhf = tmp_path / "DHF"
        srs = dhf / "config" / "doc_types" / "srs.yaml"
        doc = yaml.safe_load(srs.read_text())
        doc["properties"].append(
            {"name": "supersedes", "format": "relationship", "label": "Supersedes"}
        )
        srs.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))

        config = ProjectConfig.load(dhf / "config")
        assert "supersedes" in config.relationship_fields()

        item = next((dhf / "items").rglob("SRS-*.yaml"))
        data = yaml.safe_load(item.read_text())
        data["supersedes"] = ["ZZZ-999"]
        item.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

        result = LocalDHFAdapter(dhf).validate_traceability()
        assert any(d["field"] == "supersedes" for d in result.get("dangling", []))
