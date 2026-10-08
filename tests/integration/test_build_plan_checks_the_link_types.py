"""`build plan` must find what `verify dhf` will fail on, so a run it calls ok does not fail in CI.

`verify dhf` fails a link whose target is of a type the field does not allow;
the post-plan check named dangling links and cycles but not these.
"""

from __future__ import annotations

from pathlib import Path

from medharness.scaffold import replace_placeholders, scaffold_dhf
from medharness.services.design_validation import validate_dhf_structure


def test_a_link_to_the_wrong_type_is_reported_before_ci_fails_on_it(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Typed")
    dhf = tmp_path / "DHF"
    assert not [e for e in validate_dhf_structure(dhf) if "mistyped" in e["field"]]

    # The store refuses this write; a hand edit or a merge does not.
    crs = next((dhf / "items").rglob("CRS-001.yaml"))
    crs.write_text(crs.read_text(encoding="utf-8") + "derives_from:\n- SYS-001\n", encoding="utf-8")

    [found] = [e for e in validate_dhf_structure(dhf) if "mistyped" in e["field"]]
    assert "CRS-001.derives_from → SYS-001" in found["issue"]
    assert "UC" in found["issue"]
