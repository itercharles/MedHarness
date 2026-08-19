"""Tests for `medharness verify dhf` blocking semantics and output labelling.

Two invariants are pinned here:

1. A dangling link always blocks — it is a broken reference, not a design gap.
2. Uncovered items are advisory unless --fail-on-uncovered is passed, and must
   never print FAIL while the command exits 0. A CI log full of FAIL lines on a
   green build tells the reader the gate ran when it did not.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from medharness.cli import main
from medharness.services.ci import ci_structural_gate
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf


def _scaffold(tmp_path: Path) -> Path:
    _scaffold_dhf(tmp_path)
    _replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _break_link(dhf: Path, glob: str, old: str, new: str) -> None:
    matches = list((dhf / "items").rglob(glob))
    assert matches, f"no item matched {glob}"
    path = matches[0]
    text = path.read_text()
    assert old in text, f"{old} not in {path.name}"
    path.write_text(text.replace(old, new))


class TestDanglingAlwaysBlocks:
    def test_dangling_link_fails_without_any_flag(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        _break_link(dhf, "RCM-*.yaml", "RISK-001", "RISK-404")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
        assert r.exit_code != 0, r.output
        assert "FAIL [dangling]" in r.output
        assert "RISK-404" in r.output

    def test_service_marks_gate_failed(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        _break_link(dhf, "RCM-*.yaml", "RISK-001", "RISK-404")
        result = ci_structural_gate(dhf_path=dhf)
        assert result["passed"] is False
        assert result["results"]["traceability"]["dangling"]

    def test_fix_hint_points_at_the_reference_not_the_link(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        _break_link(dhf, "RCM-*.yaml", "RISK-001", "RISK-404")
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
        assert "correct the ID" in r.output
        assert "resolves to nothing" in r.output

    def test_clean_scaffold_passes(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
        assert r.exit_code == 0, r.output
        assert "FAIL" not in r.output


class TestCoverageIsAdvisoryByDefault:
    def _strip_swdd(self, dhf: Path) -> None:
        for path in (dhf / "items").rglob("SWDD-*.yaml"):
            path.unlink()

    def test_gap_prints_warn_and_exits_zero(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        self._strip_swdd(dhf)
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
        assert r.exit_code == 0, r.output
        assert "WARN [coverage]" in r.output
        assert "FAIL [coverage]" not in r.output

    def test_advisory_note_explains_how_to_enforce(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        self._strip_swdd(dhf)
        r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf"])
        assert "--fail-on-uncovered" in r.output

    def test_flag_makes_gap_blocking(self, tmp_path: Path) -> None:
        dhf = _scaffold(tmp_path)
        self._strip_swdd(dhf)
        r = CliRunner().invoke(
            main, ["--dhf", str(dhf), "verify", "dhf", "--fail-on-uncovered"]
        )
        assert r.exit_code != 0, r.output
        assert "FAIL [coverage]" in r.output

    def test_json_passed_matches_exit_code(self, tmp_path: Path) -> None:
        """The JSON contract and the exit code must not disagree."""
        dhf = _scaffold(tmp_path)
        self._strip_swdd(dhf)
        for flags, expect_pass in (([], True), (["--fail-on-uncovered"], False)):
            r = CliRunner().invoke(main, ["--dhf", str(dhf), "verify", "dhf", *flags])
            payload = json.loads(r.output.splitlines()[0])
            assert payload["passed"] is expect_pass
            assert (r.exit_code == 0) is expect_pass


class TestScaffoldWorkflowEnforcesCoverage:
    def test_shipped_ci_template_passes_the_flag(self, tmp_path: Path) -> None:
        """The scaffolded pipeline must actually enforce what it reports."""
        _scaffold_dhf(tmp_path)
        workflow = (tmp_path / ".github" / "workflows" / "dhf.yml").read_text()
        assert "verify dhf --dhf DHF --fail-on-uncovered" in workflow
