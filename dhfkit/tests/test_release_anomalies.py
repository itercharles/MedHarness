"""Tests for known anomalies in the release record (IEC 62304 §9.7).

A release may ship with unresolved defects — the standard does not forbid it.
What it requires is that they are documented and assessed. The REL item carried
`title · version · content · included_items · release_notes` and nothing
connected an open defect to the release shipping with it.

The mechanism mirrors SOUP `accepted_vulns`: an assessment recorded against the
specific finding, never a blanket suppression.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from dhfkit.release_baseline import _collect_known_anomalies, build_release_baseline

DEFECT = """id: {uid}
title: {title}
description: Observed in a long-running session.
steps_to_reproduce: Load a large series and export.
severity: {severity}
status: {status}
"""


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    """Built from bundled templates — dhfkit's suite must not import medharness."""
    templates = Path(__file__).resolve().parents[1] / "templates"
    root = tmp_path / "DHF"
    for src, dst in (("config", "config"), ("items", "items")):
        source = templates / src
        if source.is_dir():
            shutil.copytree(source, root / dst, dirs_exist_ok=True)
    return root


def _defect(dhf: Path, uid: str, status: str, *, severity: str = "Low",
            rationale: str = "", title: str = "Export drops a contour") -> None:
    body = DEFECT.format(uid=uid, title=title, severity=severity, status=status)
    if rationale:
        body += f"release_rationale: {rationale}\n"
    target = dhf / "items" / "12_def"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{uid}.yaml").write_text(body)


def _baseline(dhf: Path, out: Path, version: str = "1.0.0", write: bool = False) -> dict:
    return build_release_baseline(dhf, version, [], [], out, write=write)


class TestAnomalyCollection:
    @pytest.mark.parametrize("status", ["draft", "open", "in_progress"])
    def test_unresolved_states_are_collected(self, dhf: Path, status: str) -> None:
        _defect(dhf, "DEF-001", status, rationale="Assessed under RISK-001.")
        anomalies, errors = _collect_known_anomalies(dhf)
        assert [a["defect"] for a in anomalies] == ["DEF-001"]
        assert errors == []

    @pytest.mark.parametrize("status", ["resolved", "closed", "cancelled"])
    def test_settled_states_are_not_anomalies(self, dhf: Path, status: str) -> None:
        """A cancelled report means the report was withdrawn, not that it shipped."""
        _defect(dhf, "DEF-001", status)
        anomalies, errors = _collect_known_anomalies(dhf)
        assert anomalies == []
        assert errors == []

    def test_carries_severity_and_state(self, dhf: Path) -> None:
        _defect(dhf, "DEF-001", "open", severity="High", rationale="Assessed.")
        entry = _collect_known_anomalies(dhf)[0][0]
        assert entry["severity"] == "High"
        assert entry["state"] == "open"
        assert entry["title"]

    def test_output_is_sorted(self, dhf: Path) -> None:
        for uid in ("DEF-003", "DEF-001", "DEF-002"):
            _defect(dhf, uid, "open", rationale="Assessed.")
        anomalies, _ = _collect_known_anomalies(dhf)
        assert [a["defect"] for a in anomalies] == ["DEF-001", "DEF-002", "DEF-003"]


class TestGate:
    def test_unassessed_defect_blocks_the_baseline(self, dhf: Path, tmp_path: Path) -> None:
        """The deliberate break: shipping an unassessed anomaly is not allowed."""
        _defect(dhf, "DEF-001", "open")

        result = _baseline(dhf, tmp_path / "out")

        assert result["outcome"] == "completed_with_errors"
        assert result["rel_uid"] is None
        assert any("§9.7" in e for e in result["errors"])

    def test_assessed_defect_passes_and_is_recorded(self, dhf: Path, tmp_path: Path) -> None:
        _defect(dhf, "DEF-001", "open",
                rationale="Unreachable in the released configuration.")

        result = _baseline(dhf, tmp_path / "out")

        assert result["outcome"] == "completed", result["errors"]
        assert result["known_anomalies"][0]["defect"] == "DEF-001"

    def test_error_names_the_defect_and_what_to_do(self, dhf: Path, tmp_path: Path) -> None:
        _defect(dhf, "DEF-007", "in_progress")
        error = _baseline(dhf, tmp_path / "out")["errors"][0]
        assert "DEF-007" in error
        assert "release_rationale" in error
        assert "resolve it" in error

    def test_no_defects_is_not_a_gap(self, dhf: Path, tmp_path: Path) -> None:
        result = _baseline(dhf, tmp_path / "out")
        assert result["outcome"] == "completed", result["errors"]
        assert result["known_anomalies"] == []

    def test_one_unassessed_among_several_blocks(self, dhf: Path, tmp_path: Path) -> None:
        _defect(dhf, "DEF-001", "open", rationale="Assessed.")
        _defect(dhf, "DEF-002", "open")

        result = _baseline(dhf, tmp_path / "out")
        assert result["outcome"] == "completed_with_errors"
        assert len(result["errors"]) == 1
        assert "DEF-002" in result["errors"][0]


class TestArtifactAndRecord:
    def test_baseline_artifact_carries_the_anomalies(self, dhf: Path, tmp_path: Path) -> None:
        _defect(dhf, "DEF-001", "open", rationale="Assessed under RISK-001.")
        out = tmp_path / "out"

        _baseline(dhf, out)

        payload = json.loads((out / "release-baseline.json").read_text())
        assert payload["known_anomalies"][0]["defect"] == "DEF-001"
        assert "RISK-001" in payload["known_anomalies"][0]["rationale"]

    def test_rel_item_carries_them_too(self, dhf: Path, tmp_path: Path) -> None:
        """The record, not only the generated artifact."""
        import dhfkit.api as api

        _defect(dhf, "DEF-001", "open", rationale="Assessed under RISK-001.")
        result = _baseline(dhf, tmp_path / "out", write=True)

        assert result["rel_uid"], result["errors"]
        rel = api.get_item(dhf, result["rel_uid"])
        assert rel["known_anomalies"][0]["defect"] == "DEF-001"


class TestBaselineRunsAtAll:
    """A pre-existing crash found while building this phase."""

    def test_scaffold_with_soup_does_not_crash(self, dhf: Path, tmp_path: Path) -> None:
        """`release-baseline` read item["uid"], but items expose "id".

        Every scaffolded DHF ships a SOUP item, so the §9 release baseline
        command — a regulatory deliverable — raised KeyError on any default
        project.
        """
        result = _baseline(dhf, tmp_path / "out")
        assert result["outcome"] == "completed", result["errors"]
        assert result["soup_count"] >= 1

    def test_bom_artifact_keeps_its_uid_key(self, dhf: Path, tmp_path: Path) -> None:
        """Consumers read "uid" from the artifact; only the lookup was wrong."""
        out = tmp_path / "out"
        _baseline(dhf, out)
        bom = json.loads((out / "software-bom.json").read_text())
        assert bom["dhf_soup"][0]["uid"].startswith("SOUP-")
