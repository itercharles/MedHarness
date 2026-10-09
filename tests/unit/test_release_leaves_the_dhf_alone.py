"""`build release` without `--write` does not change the DHF.

Its specifications were rendered into `DHF/documents/specs/` and
`DHF/documents/exports/` and then copied to `--out-dir`, so a dry run left the
working tree modified.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from fixtures.starter import keep_the_starter_text

from medharness.services.release import build_release


def _project(tmp_path: Path) -> Path:
    from medharness.scaffold import replace_placeholders, scaffold_dhf

    scaffold_dhf(tmp_path / "project")
    replace_placeholders(tmp_path / "project", "Untouched")
    keep_the_starter_text(tmp_path / "project" / "DHF")
    return tmp_path / "project"


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_a_dry_run_writes_only_to_the_out_dir(tmp_path: Path) -> None:
    project = _project(tmp_path)
    before = _snapshot(project)

    result = build_release(project / "DHF", "1.0.0", tmp_path / "out", write=False)

    assert result["errors"] == [], result["errors"]
    assert _snapshot(project) == before


def test_the_specifications_still_reach_the_out_dir(tmp_path: Path) -> None:
    """Otherwise the test above passes on a release that renders nothing."""
    project = _project(tmp_path)

    build_release(project / "DHF", "1.0.0", tmp_path / "out", write=False)

    specs = list((tmp_path / "out").rglob("specifications/SRS_Specification_*.html"))
    assert specs and "SRS-001" in specs[0].read_text(encoding="utf-8")


def test_the_specifications_render_the_items_as_they_are(tmp_path: Path) -> None:
    from dhfkit.store import open_store

    project = _project(tmp_path)
    open_store(project / "DHF").update_item("SRS-001", {"title": "Renamed just before release"})

    build_release(project / "DHF", "1.0.0", tmp_path / "out", write=False)

    spec = tmp_path / "out" / "specifications" / "SRS_Specification_1.0.0.html"
    assert "Renamed just before release" in spec.read_text(encoding="utf-8")
def test_the_traceability_report_follows_the_configured_chain(tmp_path: Path) -> None:
    """The report's columns come from the first `traceability_matrices` chain."""
    project = _project(tmp_path)
    (project / "DHF" / "config" / "global.yaml").write_text(
        "project_name: Untouched\n"
        "traceability_matrices:\n"
        "  - name: Short chain\n"
        "    description: System to software only\n"
        "    path: [SYS, SRS]\n"
    )
    build_release(project / "DHF", "1.0.0", tmp_path / "out", write=False)
    import json

    report = tmp_path / "out" / "traceability" / "Requirements_Traceability_Report.json"
    assert json.loads(report.read_text(encoding="utf-8"))["columns"] == ["SYS", "SRS"]
