"""Tests for derived verification status, coverage gating, and CR phases.

Each case here reproduces a defect that made the DHF misreport something
compliance-load-bearing:

* an item claimed ``verified`` with an empty result store, and flipped to
  ``not_verified`` when an *unrelated* result was added;
* ``evidence bundle --junit`` wiped verification that lived only in the result
  store, including manual review records that can never appear in a JUnit file;
* a typo in ``--coverage-pair`` reported ``passed: True`` over zero items;
* ``change plan --cr CR-001`` on a freshly scaffolded project answered
  "CR 'CR-001' not found" for the CR the scaffold had just written.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dhfkit.local_adapter import LocalDHFAdapter
from medharness.core import MedHarnessCore
from medharness.workflows.cr_state import (
    ACTIVE_PHASES,
    TERMINAL_PHASES,
    CRPhase,
    assert_cr_active,
    get_cr_phase,
)
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _core(dhf: Path) -> MedHarnessCore:
    return MedHarnessCore(LocalDHFAdapter(dhf))


def _record(dhf: Path, tc_id: str, links: list[str], status: str = "PASS",
            reviewer: str = "") -> None:
    """Record a result. Passing `reviewer` makes it a manual review record."""
    entry = {"tc_id": tc_id, "testing_status": status, "links": links}
    if reviewer:
        entry.update({"reviewer": reviewer, "review_status": "approved"})
    LocalDHFAdapter(dhf)._result_store.record_executions([entry])


def _junit(path: Path, links: str, failed: bool = False) -> Path:
    failure = "<failure message='boom'>x</failure>" if failed else ""
    path.write_text(
        "<testsuites><testsuite name='s' tests='1'>"
        "<testcase classname='t' name='test_x' time='0.1'>"
        f"<properties><property name='medharness.links' value='{links}'/></properties>"
        f"{failure}</testcase></testsuite></testsuites>"
    )
    return path


class TestVerificationRequiresEvidence:
    def test_empty_store_does_not_leave_a_stale_verified(self, dhf: Path) -> None:
        """A YAML claiming verified with no results must not be believed."""
        srs = next((dhf / "items" / "03_srs").glob("SRS-*.yaml"))
        srs.write_text(srs.read_text() + "\nverification_status: verified\n")

        assert _core(dhf).get_item("SRS-001")["verification_status"] == "not_verified"

    def test_status_does_not_depend_on_unrelated_items(self, dhf: Path) -> None:
        """Previously: empty store said verified, one unrelated result said not."""
        srs = next((dhf / "items" / "03_srs").glob("SRS-*.yaml"))
        srs.write_text(srs.read_text() + "\nverification_status: verified\n")
        before = _core(dhf).get_item("SRS-001")["verification_status"]

        _record(dhf, "TC-SYS-001", ["SYS-001"])
        after = _core(dhf).get_item("SRS-001")["verification_status"]

        assert before == after == "not_verified"

    def test_linked_passing_result_verifies(self, dhf: Path) -> None:
        _record(dhf, "TC-SRS-001", ["SRS-001"])
        assert _core(dhf).get_item("SRS-001")["verification_status"] == "verified"

    def test_linked_failing_result_marks_failed(self, dhf: Path) -> None:
        _record(dhf, "TC-SRS-001", ["SRS-001"], status="FAIL")
        assert _core(dhf).get_item("SRS-001")["verification_status"] == "failed"


class TestJunitInjectionMerges:
    """Merge only what a JUnit run cannot carry.

    Manual review records live solely in the store and must survive. Ordinary
    automated results are superseded by the batch — otherwise deleting a test
    left its requirement `verified` by a stale stored PASS.
    """

    def test_manual_review_record_survives_an_unrelated_junit(self, dhf: Path, tmp_path: Path) -> None:
        _record(dhf, "TC-SRS-001", ["SRS-001"], reviewer="qa@example.com")
        core = _core(dhf)
        assert core.get_item("SRS-001")["verification_status"] == "verified"

        core.inject_junit_results([_junit(tmp_path / "sys.xml", "SYS-001")])

        assert core.get_item("SRS-001")["verification_status"] == "verified"
        assert core.get_item("SYS-001")["verification_status"] == "verified"

    def test_stale_automated_result_does_not_survive(self, dhf: Path, tmp_path: Path) -> None:
        """A deleted test must drop its requirement, not leave it verified."""
        _record(dhf, "TC-SRS-001", ["SRS-001"])
        core = _core(dhf)
        assert core.get_item("SRS-001")["verification_status"] == "verified"

        # The batch no longer contains a test for SRS-001 — it was deleted.
        core.inject_junit_results([_junit(tmp_path / "sys.xml", "SYS-001")])

        assert core.get_item("SRS-001")["verification_status"] == "not_verified"

    def test_junit_overrides_the_store_for_the_same_item(self, dhf: Path, tmp_path: Path) -> None:
        _record(dhf, "TC-SRS-001", ["SRS-001"])
        core = _core(dhf)

        core.inject_junit_results([_junit(tmp_path / "srs.xml", "SRS-001", failed=True)])

        assert core.get_item("SRS-001")["verification_status"] == "failed"

    def test_item_with_no_evidence_anywhere_is_not_verified(self, dhf: Path, tmp_path: Path) -> None:
        core = _core(dhf)
        core.inject_junit_results([_junit(tmp_path / "sys.xml", "SYS-001")])
        assert core.get_item("SRS-001")["verification_status"] == "not_verified"


class TestCoverageTypeValidation:
    def test_unknown_type_code_fails_instead_of_passing_vacuously(self, dhf: Path) -> None:
        result = _core(dhf).check_coverage([("NOPE", "CRS")])
        assert result["passed"] is False
        assert "unknown document type" in result["results"][0]["error"]

    def test_error_names_the_configured_codes(self, dhf: Path) -> None:
        result = _core(dhf).check_coverage([("SYS", "TYPO")])
        assert "TYPO" in result["results"][0]["error"]
        assert "SRS" in result["results"][0]["error"]

    def test_known_codes_still_evaluate(self, dhf: Path) -> None:
        result = _core(dhf).check_coverage([("SYS", "SRS")])
        assert result["results"][0]["total"] > 0
        assert "error" not in result["results"][0]


class TestPrefixResolution:
    def test_prefix_comes_from_config_not_from_the_code(self, dhf: Path) -> None:
        """get_item_type matches on prefix, so passing a code never resolved."""
        core = _core(dhf)
        assert core._get_prefix("SYS") == "SYS-"
        assert core._get_prefix("SYSARCH") == "SYSARCH-"

    def test_multi_segment_prefix_resolves(self, dhf: Path) -> None:
        (dhf / "config" / "doc_types" / "tcver.yaml").write_text(
            "code: TCVER\nname: Verification Test Case\nprefix: TC-VER-\n"
            "directory: 13_tcver\nfields:\n- name: title\n  format: short_text\n"
            "  label: Title\n"
        )
        assert _core(dhf)._get_prefix("TCVER") == "TC-VER-"

    def test_unknown_code_returns_none(self, dhf: Path) -> None:
        assert _core(dhf)._get_prefix("NOPE") is None


class TestCRPhases:
    def test_scaffolded_cr_is_active(self, dhf: Path) -> None:
        """The documented first command must work on a fresh project."""
        assert assert_cr_active(LocalDHFAdapter(dhf), "CR-001") in ACTIVE_PHASES

    def test_missing_cr_says_not_found(self, dhf: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            assert_cr_active(LocalDHFAdapter(dhf), "CR-999")

    def test_absent_status_reads_as_new(self, dhf: Path) -> None:
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new\n", ""))
        assert get_cr_phase(LocalDHFAdapter(dhf), "CR-001") is CRPhase.NEW

    def test_rejected_is_terminal_not_missing(self, dhf: Path) -> None:
        """generate-dhf triage writes 'rejected'; it was read as 'not found'."""
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new", "status: rejected"))

        with pytest.raises(ValueError) as exc:
            assert_cr_active(LocalDHFAdapter(dhf), "CR-001")
        assert "not found" not in str(exc.value)
        assert "rejected" in str(exc.value)

    def test_unrecognised_status_is_reported_as_such(self, dhf: Path) -> None:
        cr = dhf / "items" / "07_cr" / "CR-001.yaml"
        cr.write_text(cr.read_text().replace("status: new", "status: banana"))

        with pytest.raises(ValueError) as exc:
            assert_cr_active(LocalDHFAdapter(dhf), "CR-001")
        assert "not found" not in str(exc.value)
        assert "banana" in str(exc.value)

    def test_rejected_is_a_terminal_phase(self) -> None:
        assert CRPhase.REJECTED in TERMINAL_PHASES
        assert CRPhase.REJECTED not in ACTIVE_PHASES


class TestIssueCommentPagination:
    """gh api truncates at 100 without --paginate; --slurp then nests the pages."""

    def _call(self, monkeypatch, stdout: str):
        import subprocess
        from medharness import _helpers

        captured = {}

        def _fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout, "")

        monkeypatch.setattr(_helpers.subprocess, "run", _fake_run)
        result = _helpers._load_issue_comments(
            comments_path=None, source_repo="acme/cl",
            issue_number=7, source_token="t",
        )
        return result, captured["command"]

    def test_paginate_and_slurp_are_requested(self, monkeypatch) -> None:
        _, command = self._call(monkeypatch, "[[]]")
        assert "--paginate" in command
        assert "--slurp" in command

    def test_pages_are_flattened(self, monkeypatch) -> None:
        stdout = '[[{"body":"a"},{"body":"b"}],[{"body":"c"}]]'
        result, _ = self._call(monkeypatch, stdout)
        assert [c["body"] for c in result] == ["a", "b", "c"]

    def test_unslurped_array_still_accepted(self, monkeypatch) -> None:
        result, _ = self._call(monkeypatch, '[{"body":"a"}]')
        assert [c["body"] for c in result] == ["a"]
