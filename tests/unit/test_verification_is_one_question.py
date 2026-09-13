"""Coverage and verification method are one question, asked once.

They used to be two gates with identical inputs. A requirement verified by
Inspection has no test by design: `verify tests` reported it uncovered while
`verify verification` reported it as needing a sign-off. Neither was wrong about
its half, and nothing put the halves together.

Asked as one question, the declared method decides what counts as verified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medharness.services.ci import ci_test_coverage_gate


def _dhf(tmp_path: Path, items: list[dict]) -> Path:
    """A real minimal DHF, scaffolded the way dhfkit does it."""
    from click.testing import CliRunner

    from dhfkit.cli import main as dhfkit_main

    dhf = tmp_path / "DHF"
    CliRunner().invoke(dhfkit_main, ["--dhf", str(dhf), "init"])
    items_dir = dhf / "items" / "03_srs"
    items_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        lines = [f"id: {item['id']}", "title: t", "status: draft"]
        if "verification_method" in item:
            lines.append("verification_method:")
            lines += [f"  - {v}" for v in item["verification_method"]]
        (items_dir / f"{item['id']}.yaml").write_text("\n".join(lines) + "\n")
    return dhf


def _junit(tmp_path: Path, body: str = "") -> Path:
    p = tmp_path / "results.xml"
    p.write_text(f'<testsuite name="s" tests="1">{body}</testsuite>')
    return p


class TestTheDeclaredMethodDecides:
    def test_an_inspection_item_is_not_reported_as_a_test_gap(self, tmp_path: Path) -> None:
        dhf = _dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Inspection"]}])
        result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[_junit(tmp_path)])
        details = result["details"]
        assert not details["unverified_test"], (
            "an item verified by Inspection was reported as missing a test"
        )
        assert [g["id"] for g in details["manual_review_required"]] == ["SRS-001"]

    def test_a_test_item_with_no_passing_case_fails(self, tmp_path: Path) -> None:
        dhf = _dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
        result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[_junit(tmp_path)])
        assert [g["id"] for g in result["details"]["unverified_test"]] == ["SRS-001"]
        assert result["passed"] is False
        assert any("declares Test but no passing case" in e for e in result["errors"]), (
            "the verdict came from coverage alone; the method classification is "
            "not reaching the errors, so removing it would not be noticed"
        )


class TestAMissingMethodWarnsUntilAsked:
    """A project adding the field has a gap on every item at first."""

    def test_it_warns_by_default(self, tmp_path: Path) -> None:
        dhf = _dhf(tmp_path, [{"id": "SRS-001"}])
        result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[_junit(tmp_path)])
        assert [g["id"] for g in result["details"]["missing_method"]] == ["SRS-001"]
        assert any("no verification_method" in w for w in result["warnings"])

    def test_require_method_blocks(self, tmp_path: Path) -> None:
        dhf = _dhf(tmp_path, [{"id": "SRS-001"}])
        result = ci_test_coverage_gate(
            dhf_path=dhf, junit_paths=[_junit(tmp_path)], require_method=True,
        )
        assert result["passed"] is False


class TestWithoutEvidence:
    def test_missing_junit_still_fails(self, tmp_path: Path) -> None:
        """The gate confirms tests ran and passed. It cannot, so it fails."""
        dhf = _dhf(tmp_path, [{"id": "SRS-001", "verification_method": ["Test"]}])
        result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[])
        assert result["passed"] is False

    def test_the_method_check_still_runs(self, tmp_path: Path) -> None:
        """Declaring a method needs no test run; the early return used to skip it."""
        dhf = _dhf(tmp_path, [{"id": "SRS-001"}])
        result = ci_test_coverage_gate(dhf_path=dhf, junit_paths=[])
        assert [g["id"] for g in result["details"]["missing_method"]] == ["SRS-001"]


def test_the_separate_gate_is_gone() -> None:
    import click

    from medharness.cli import main

    assert "verification" not in main.commands["verify"].commands, (
        "verify verification is back; two gates with the same inputs will "
        "disagree about an Inspection-verified requirement again"
    )
