"""What an agent is told about the DHF must match what the gate decides.

`traceability.valid` used to be computed from coverage alone, so a DHF whose
links formed a cycle was reported sound to the agent while `verify dhf` failed
the same DHF. An agent cannot fix what it is told is already fine.
"""

from __future__ import annotations

import json

import pytest

from medharness.cli.dhf import _traceability_summary

CYCLE = {
    "passed": False,
    "coverage": [{"parent_type": "SYS", "child_type": "SRS",
                  "covered": 1, "total": 1, "uncovered": []}],
    "cycles": [["CRS-001", "SYS-001"]],
    "dangling": [],
    "required": {"failures": []},
}


class TestValidIsTheWholeVerdict:
    def test_a_cycle_with_full_coverage_is_not_valid(self) -> None:
        summary = _traceability_summary(CYCLE)
        assert summary["valid"] is False, (
            "every coverage pair is complete, so a coverage-only verdict says "
            "valid; the DHF has a cycle and `verify dhf` fails it"
        )

    def test_the_cycle_is_named_not_just_counted(self) -> None:
        assert _traceability_summary(CYCLE)["cycles"] == [["CRS-001", "SYS-001"]]

    def test_a_dangling_link_with_full_coverage_is_not_valid(self) -> None:
        trace = {**CYCLE, "cycles": [], "dangling": [{"id": "SRS-001", "target": "SYS-404"}]}
        assert _traceability_summary(trace)["valid"] is False

    def test_a_required_traceability_failure_is_not_valid(self) -> None:
        trace = {**CYCLE, "cycles": [],
                 "required": {"failures": [{"id": "SYS-002", "issue": "no SRS"}]}}
        assert _traceability_summary(trace)["valid"] is False
        assert _traceability_summary(trace)["required_failures"]

    def test_a_sound_dhf_is_valid(self) -> None:
        trace = {**CYCLE, "passed": True, "cycles": []}
        assert _traceability_summary(trace)["valid"] is True

    def test_valid_tracks_passed_and_is_not_recomputed(self) -> None:
        """`analyse` owns the verdict; the summary reports it."""
        assert _traceability_summary({**CYCLE, "passed": True})["valid"] is True


class TestAgainstARealDhf:
    def test_overview_and_verify_dhf_agree_on_a_cyclic_dhf(self, tmp_path) -> None:
        from click.testing import CliRunner

        from medharness.cli import main
        from medharness.services.ci import ci_structural_gate

        dhf = _scaffold(tmp_path)
        _make_a_cycle(dhf)

        gate = ci_structural_gate(dhf)
        assert gate["passed"] is False, "the gate should fail a DHF with a cycle"

        result = CliRunner().invoke(main, ["--dhf", str(dhf), "context", "overview"])
        assert result.exit_code == 0, result.output
        reported = json.loads(result.stdout)["traceability"]["valid"]
        assert reported is False, "the gate fails this DHF; the agent was told it is valid"

    def test_project_survives_a_relative_dhf_path(self, tmp_path) -> None:
        """`--dhf DHF` is how the docs and the CI recipe invoke it, and
        `Path("DHF").parent.name` is the empty string."""
        import os

        from click.testing import CliRunner

        from medharness.cli import main

        dhf = _scaffold(tmp_path)
        cwd = os.getcwd()
        try:
            os.chdir(dhf.parent)
            result = CliRunner().invoke(main, ["--dhf", "DHF", "context", "overview"])
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["project"], "project name came back empty"


def _scaffold(tmp_path):
    import subprocess
    import sys

    subprocess.run([sys.executable, "-c",
                    "from medharness.cli import main; main()", "init"],
                   cwd=tmp_path, capture_output=True, check=False)
    dhf = tmp_path / "DHF"
    if not (dhf / "config" / "global.yaml").exists():
        pytest.skip("scaffold unavailable")
    return dhf


def _make_a_cycle(dhf):
    """CRS-001 already satisfies SYS-001; point it back so neither has an origin.

    Coverage stays complete, which is the point: a coverage-only verdict passes.
    """
    crs = dhf / "items" / "01_crs" / "CRS-001.yaml"
    crs.write_text(
        crs.read_text().replace("derives_from:\n  - UC-001",
                                "derives_from:\n  - UC-001\n  - SYS-001"),
        encoding="utf-8",
    )
