"""Unit tests for medharness.services.code_validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from medharness.services.code_validation import (
    _annotation_present,
    validate_code,
)


def _write_spec(path: Path, needs_new_tc: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "---\n"
        'cr_id: "CR-050"\n'
        'direction_fit: "in-scope"\n'
        "affected_items: []\n"
        "test_plan:\n"
        "  auto_covered: []\n"
        "  needs_new_tc:"
    )
    if needs_new_tc:
        body += "\n" + "\n".join(f"    - {uid}" for uid in needs_new_tc)
    else:
        body += " []"
    body += "\n  must_be_manual: []\n---\n"
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    dhf = tmp_path / "DHF"
    dhf.mkdir()
    spec = tmp_path / "docs" / "cr-specs" / "CR-050-Spec.md"
    return dhf, spec


def _diff(stdout: str, returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=stdout, returncode=returncode)


class TestAnnotationPresent:
    def test_single_id_match(self):
        text = "// @links:SRS-001 — covers requirement"
        assert _annotation_present(text, "SRS-001")

    def test_grouped_match(self):
        text = "/** @links:SRS-001,SRS-002,SRS-003 */"
        assert _annotation_present(text, "SRS-002")

    def test_substring_does_not_match_outside_marker(self):
        text = "// note: SRS-001 was changed"
        assert not _annotation_present(text, "SRS-001")

    def test_no_partial_id_match(self):
        text = "// @links:SRS-0011 covers SRS-0011 only"
        assert not _annotation_present(text, "SRS-001")


class TestValidateCode:
    def test_passes_when_annotation_in_diff(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001"])
        diff = (
            "+++ b/apps/client/src/foo.test.ts\n"
            "+// @links:SRS-001 — covers focal-point reslicing\n"
            "+it('reslices', () => { expect(true).toBe(true); });\n"
        )
        with patch("subprocess.run", return_value=_diff(diff)):
            errors = validate_code("CR-050", dhf, spec)
        assert errors == []

    def test_flags_missing_annotation(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001", "SRS-002"])
        diff = (
            "+++ b/apps/client/src/foo.test.ts\n"
            "+// @links:SRS-001 — partial coverage\n"
        )
        with patch("subprocess.run", return_value=_diff(diff)):
            errors = validate_code("CR-050", dhf, spec)
        assert len(errors) == 1
        assert "SRS-002" in errors[0]["issue"]

    def test_does_not_count_removed_annotations(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001"])
        diff = (
            "--- a/apps/client/src/foo.test.ts\n"
            "+++ b/apps/client/src/foo.test.ts\n"
            "-// @links:SRS-001 — removed coverage\n"
        )
        with patch("subprocess.run", return_value=_diff(diff)):
            errors = validate_code("CR-050", dhf, spec)
        assert len(errors) == 1
        assert "SRS-001" in errors[0]["issue"]

    def test_grouped_annotation_satisfies_multiple_ids(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001", "SRS-002"])
        diff = (
            "+++ b/apps/client/src/foo.test.ts\n"
            "+/** @links:SRS-001,SRS-002 */\n"
        )
        with patch("subprocess.run", return_value=_diff(diff)):
            errors = validate_code("CR-050", dhf, spec)
        assert errors == []

    def test_empty_needs_new_tc_returns_no_errors(self, repo):
        dhf, spec = repo
        _write_spec(spec, [])
        # subprocess should not even be called when there is nothing to check
        with patch("subprocess.run") as mock_run:
            errors = validate_code("CR-050", dhf, spec)
        assert errors == []
        mock_run.assert_not_called()

    def test_missing_spec_returns_no_errors(self, repo):
        dhf, _ = repo
        nonexistent = repo[1]
        errors = validate_code("CR-050", dhf, nonexistent)
        assert errors == []

    def test_git_unavailable_yields_single_environment_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001", "SRS-002"])
        with patch("subprocess.run", side_effect=FileNotFoundError):
            errors = validate_code("CR-050", dhf, spec)
        # An env failure must not be fabricated as per-item annotation errors;
        # the LLM cannot fix a missing `git fetch`.
        assert len(errors) == 1
        assert errors[0]["field"] == "environment"
        assert "git diff" in errors[0]["issue"]
        assert "git fetch" in errors[0]["fix"]

    def test_git_nonzero_exit_yields_single_environment_error(self, repo):
        dhf, spec = repo
        _write_spec(spec, ["SRS-001", "SRS-002"])
        with patch("subprocess.run", return_value=_diff("", returncode=128)):
            errors = validate_code("CR-050", dhf, spec)
        assert len(errors) == 1
        assert errors[0]["field"] == "environment"

    def test_legitimate_empty_diff_still_flags_missing_annotations(self, repo):
        # git ran successfully but reported zero changes — the spec said new
        # tests were needed, so flagging the gap is correct (this is distinct
        # from an env failure).
        dhf, spec = repo
        _write_spec(spec, ["SRS-001"])
        with patch("subprocess.run", return_value=_diff("", returncode=0)):
            errors = validate_code("CR-050", dhf, spec)
        assert len(errors) == 1
        assert errors[0]["field"] == "test_plan.needs_new_tc"
        assert "SRS-001" in errors[0]["issue"]
