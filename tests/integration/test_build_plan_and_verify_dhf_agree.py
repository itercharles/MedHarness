"""`build plan` must find every blocking thing `verify dhf` will fail on.

Both read one list of findings (`structural_findings`), so a kind of finding added
to the gate reaches the fix pass too. This breaks the DHF three ways at once and
requires the fix pass to name each error the gate reports.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf
from medharness.services.design_validation import validate_dhf_structure


def test_every_error_verify_dhf_reports_is_in_the_fix_pass(tmp_path: Path) -> None:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Agree")
    dhf = tmp_path / "DHF"
    crs = next((dhf / "items").rglob("CRS-001.yaml"))
    crs.write_text(crs.read_text(encoding="utf-8") + "derives_from:\n- SYS-001\n", encoding="utf-8")   # wrong type
    srs = next((dhf / "items").rglob("SRS-001.yaml"))
    srs.write_text(srs.read_text(encoding="utf-8").replace("derives_from:\n- SYS-001", "derives_from:\n- SYS-999"),
                   encoding="utf-8")                                                                   # dangling
    cr = next((dhf / "items").rglob("CR-001.yaml"))
    cr.write_text(cr.read_text(encoding="utf-8").replace("status: new", "status: banana"), encoding="utf-8")

    gate = json.loads(CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"]).stdout)
    assert len(gate["errors"]) >= 3, gate["errors"]

    fix_pass = {e["issue"] for e in validate_dhf_structure(dhf)}
    assert not [e for e in gate["errors"] if e not in fix_pass], (gate["errors"], fix_pass)
