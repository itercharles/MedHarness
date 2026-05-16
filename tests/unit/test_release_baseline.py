"""Unit tests for medharness.services.release_baseline."""

import json
from pathlib import Path
from unittest.mock import patch

from medharness.services.release_baseline import (
    _auto_collect_crs,
    _collect_bom,
    _generate_release_notes,
    _verify_cr_gates,
    build_release_baseline,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _cr_item(uid: str, state: str, title: str = "") -> dict:
    return {"uid": uid, "type": "CR", "state": state, "title": title}


def _rel_item(uid: str, included: list[str]) -> dict:
    return {"uid": uid, "type": "REL", "version": "0.1.0", "included_items": included}


def _req_txt(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "requirements.txt"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _verify_cr_gates
# ---------------------------------------------------------------------------

class TestVerifyCrGates:
    def test_completed_cr_passes(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-001"])
        assert violations == []

    def test_cancelled_cr_is_violation(self, tmp_path):
        # cancelled CRs are not deliverables — including them would break validate_release()
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "cancelled")):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-001"])
        assert len(violations) == 1
        assert "completed" in violations[0]["issue"]

    def test_rejected_cr_is_violation(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "rejected")):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-001"])
        assert len(violations) == 1
        assert "completed" in violations[0]["issue"]

    def test_open_cr_is_violation(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "develop")):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-001"])
        assert len(violations) == 1
        assert violations[0]["cr"] == "CR-001"
        assert "develop" in violations[0]["issue"]

    def test_missing_cr_is_violation(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=None):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-999"])
        assert violations[0]["issue"] == "CR not found"

    def test_multiple_crs_all_checked(self, tmp_path):
        def side_effect(dhf, uid):
            states = {"CR-001": "completed", "CR-002": "design"}
            return _cr_item(uid, states[uid])

        with patch("dhfkit.api.get_item", side_effect=side_effect):
            violations = _verify_cr_gates(tmp_path / "DHF", ["CR-001", "CR-002"])
        assert len(violations) == 1
        assert violations[0]["cr"] == "CR-002"


# ---------------------------------------------------------------------------
# _auto_collect_crs
# ---------------------------------------------------------------------------

class TestAutoCollectCrs:
    def test_collects_completed_unreleased_crs(self, tmp_path):
        items = [
            _cr_item("CR-001", "completed"),
            _cr_item("CR-002", "develop"),
        ]
        with patch("dhfkit.api.list_items", return_value=items):
            crs = _auto_collect_crs(tmp_path / "DHF")
        assert "CR-001" in crs
        assert "CR-002" not in crs

    def test_excludes_crs_already_in_rel(self, tmp_path):
        items = [
            _cr_item("CR-001", "completed"),
            _rel_item("REL-001", ["CR-001"]),
        ]
        with patch("dhfkit.api.list_items", return_value=items):
            crs = _auto_collect_crs(tmp_path / "DHF")
        assert "CR-001" not in crs

    def test_single_pass_over_items(self, tmp_path):
        # _auto_collect_crs must use a single list_items call, not two
        items = [
            _cr_item("CR-001", "completed"),
            _rel_item("REL-001", []),
        ]
        with patch("dhfkit.api.list_items", return_value=items) as mock_list:
            _auto_collect_crs(tmp_path / "DHF")
        assert mock_list.call_count == 1

    def test_returns_sorted(self, tmp_path):
        items = [
            _cr_item("CR-003", "completed"),
            _cr_item("CR-001", "completed"),
        ]
        with patch("dhfkit.api.list_items", return_value=items):
            crs = _auto_collect_crs(tmp_path / "DHF")
        assert crs == sorted(crs)

    def test_empty_dhf_returns_empty(self, tmp_path):
        with patch("dhfkit.api.list_items", return_value=[]):
            crs = _auto_collect_crs(tmp_path / "DHF")
        assert crs == []


# ---------------------------------------------------------------------------
# _collect_bom
# ---------------------------------------------------------------------------

class TestCollectBom:
    def test_dhf_soup_items_included(self, tmp_path):
        soup = {"uid": "SOUP-001", "type": "SOUP", "name": "requests", "version": "2.31.0",
                "manufacturer": "", "license": "Apache-2.0", "safety_class": ""}
        with patch("dhfkit.api.list_items", return_value=[soup]):
            bom, errors = _collect_bom(tmp_path / "DHF", [])
        assert errors == []
        assert len(bom["dhf_soup"]) == 1
        assert bom["dhf_soup"][0]["name"] == "requests"

    def test_manifest_packages_included(self, tmp_path):
        req = _req_txt(tmp_path, "click==8.1.7\n")
        with patch("dhfkit.api.list_items", return_value=[]):
            bom, errors = _collect_bom(tmp_path / "DHF", [req])
        assert errors == []
        assert any(p["name"] == "click" for p in bom["manifest_packages"])

    def test_unreadable_manifest_returns_error(self, tmp_path):
        bad = tmp_path / "setup.cfg"
        bad.write_text("not a manifest")
        with patch("dhfkit.api.list_items", return_value=[]):
            bom, errors = _collect_bom(tmp_path / "DHF", [bad])
        assert bom["manifest_packages"] == []
        assert len(errors) == 1
        assert "Unsupported manifest format" in errors[0]

    def test_malformed_manifest_returns_error(self, tmp_path):
        bad = tmp_path / "package.json"
        bad.write_text("{not valid json}")
        with patch("dhfkit.api.list_items", return_value=[]):
            bom, errors = _collect_bom(tmp_path / "DHF", [bad])
        assert bom["manifest_packages"] == []
        assert any("Failed to parse" in e for e in errors)

    def test_non_soup_items_excluded(self, tmp_path):
        cr = _cr_item("CR-001", "completed")
        with patch("dhfkit.api.list_items", return_value=[cr]):
            bom, errors = _collect_bom(tmp_path / "DHF", [])
        assert errors == []
        assert bom["dhf_soup"] == []


# ---------------------------------------------------------------------------
# _generate_release_notes
# ---------------------------------------------------------------------------

class TestGenerateReleaseNotes:
    def test_version_in_heading(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed", "My fix")):
            notes = _generate_release_notes("1.0.0", ["CR-001"], {"dhf_soup": [], "manifest_packages": []}, tmp_path)
        assert "# Release 1.0.0" in notes

    def test_cr_title_included(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed", "Add login")):
            notes = _generate_release_notes("1.0.0", ["CR-001"], {"dhf_soup": [], "manifest_packages": []}, tmp_path)
        assert "CR-001: Add login" in notes

    def test_soup_count_mentioned(self, tmp_path):
        soup = [{"uid": "SOUP-001", "name": "requests"}]
        with patch("dhfkit.api.get_item", return_value=None):
            notes = _generate_release_notes("1.0.0", [], {"dhf_soup": soup, "manifest_packages": []}, tmp_path)
        assert "1 SOUP component(s)" in notes

    def test_no_crs_no_cr_section(self, tmp_path):
        notes = _generate_release_notes("1.0.0", [], {"dhf_soup": [], "manifest_packages": []}, tmp_path)
        assert "Change Requests" not in notes


# ---------------------------------------------------------------------------
# build_release_baseline
# ---------------------------------------------------------------------------

class TestBuildReleaseBaseline:
    def test_gate_failure_returns_error_outcome(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "design")), \
             patch("dhfkit.api.list_items", return_value=[]):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], tmp_path / "out",
            )
        assert result["outcome"] == "completed_with_errors"
        assert len(result["gate_violations"]) == 1

    def test_gate_failure_response_has_consistent_shape(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "cancelled")), \
             patch("dhfkit.api.list_items", return_value=[]):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], tmp_path / "out",
            )
        assert result["rel_uid"] is None
        assert result["soup_count"] == 0
        assert result["manifest_packages_count"] == 0
        assert result["artifacts"] == []

    def test_cancelled_cr_fails_gate(self, tmp_path):
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "cancelled")), \
             patch("dhfkit.api.list_items", return_value=[]):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], tmp_path / "out",
            )
        assert result["outcome"] == "completed_with_errors"

    def test_happy_path_writes_artifacts(self, tmp_path):
        out = tmp_path / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], out,
            )
        assert result["outcome"] == "completed"
        assert (out / "release-baseline.json").exists()
        assert (out / "software-bom.json").exists()

    def test_artifact_contents(self, tmp_path):
        out = tmp_path / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed", "Fix")), \
             patch("dhfkit.api.list_items", return_value=[]):
            build_release_baseline(tmp_path / "DHF", "2.0.0", [], ["CR-001"], out)
        data = json.loads((out / "release-baseline.json").read_text())
        assert data["version"] == "2.0.0"
        assert "CR-001" in data["included_crs"]

    def test_write_creates_rel_item(self, tmp_path):
        out = tmp_path / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]), \
             patch("dhfkit.api.create_item", return_value={"uid": "REL-001"}) as mock_create:
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], out, write=True,
            )
        mock_create.assert_called_once()
        assert result["rel_uid"] == "REL-001"

    def test_dry_run_no_rel_item_created(self, tmp_path):
        out = tmp_path / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]), \
             patch("dhfkit.api.create_item") as mock_create:
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], out, write=False,
            )
        mock_create.assert_not_called()
        assert result["rel_uid"] is None

    def test_rel_create_failure_is_completed_with_errors(self, tmp_path):
        out = tmp_path / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]), \
             patch("dhfkit.api.create_item", side_effect=RuntimeError("dhf error")):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], ["CR-001"], out, write=True,
            )
        assert result["outcome"] == "completed_with_errors"
        assert result["rel_uid"] is None
        # Artifacts are still written even when REL creation fails
        assert (out / "release-baseline.json").exists()
        assert any("Failed to create REL" in e for e in result["errors"])

    def test_auto_collect_when_no_cr_ids(self, tmp_path):
        out = tmp_path / "out"
        items_for_list = [
            _cr_item("CR-005", "completed"),
            _rel_item("REL-001", []),
        ]
        with patch("dhfkit.api.list_items", return_value=items_for_list), \
             patch("dhfkit.api.get_item", return_value=_cr_item("CR-005", "completed")):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [], [], out,
            )
        assert "CR-005" in result["cr_ids"]

    def test_manifest_soup_in_bom(self, tmp_path):
        out = tmp_path / "out"
        req = _req_txt(tmp_path, "flask==3.0.0\n")
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]):
            build_release_baseline(
                tmp_path / "DHF", "1.0.0", [req], ["CR-001"], out,
            )
        bom = json.loads((out / "software-bom.json").read_text())
        assert any(p["name"] == "flask" for p in bom["manifest_packages"])

    def test_malformed_manifest_produces_error_outcome(self, tmp_path):
        out = tmp_path / "out"
        bad = tmp_path / "package.json"
        bad.write_text("{bad json}")
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]):
            result = build_release_baseline(
                tmp_path / "DHF", "1.0.0", [bad], ["CR-001"], out,
            )
        assert result["outcome"] == "completed_with_errors"
        assert any("Failed to parse BOM" in e for e in result["errors"])

    def test_out_dir_created_if_missing(self, tmp_path):
        out = tmp_path / "deeply" / "nested" / "out"
        with patch("dhfkit.api.get_item", return_value=_cr_item("CR-001", "completed")), \
             patch("dhfkit.api.list_items", return_value=[]):
            build_release_baseline(tmp_path / "DHF", "1.0.0", [], ["CR-001"], out)
        assert out.is_dir()
