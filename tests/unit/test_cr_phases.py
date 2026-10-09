"""Which CRs `build plan` and `build code` will work on: those `cr.yaml` still lets move.

``build plan --cr CR-001`` on a freshly scaffolded project once answered
"CR 'CR-001' not found" for the CR the scaffold had just written.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf


@pytest.fixture
def dhf(tmp_path: Path) -> Path:
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Trial")
    return tmp_path / "DHF"


def _run(dhf: Path, stage: str, cr: str = "CR-001"):
    return CliRunner().invoke(main, ["--dhf", str(dhf), "build", stage, "--cr", cr, "--prompt"])


def _set_status(dhf: Path, status: str | None) -> None:
    cr = dhf / "items" / "07_cr" / "CR-001.yaml"
    text = cr.read_text().replace("status: new\n", "")
    cr.write_text(text if status is None else text + f"status: {status}\n")


@pytest.mark.parametrize("stage", ["plan", "code"])
class TestWhichCRsTheStagesAccept:
    def test_the_scaffolded_cr_is_accepted(self, dhf: Path, stage: str) -> None:
        """The documented first command must work on a fresh project."""
        assert _run(dhf, stage).exit_code == 0

    @pytest.mark.parametrize("status", [None, "new", "design", "develop"])
    def test_a_cr_that_can_still_move_is_accepted(self, dhf: Path, stage: str, status) -> None:
        _set_status(dhf, status)
        assert _run(dhf, stage).exit_code == 0

    @pytest.mark.parametrize("status", ["completed", "rejected", "cancelled"])
    def test_a_cr_with_no_move_left_is_refused_and_named(self, dhf: Path, stage: str, status: str) -> None:
        """`build plan` triage writes 'rejected'; it was once read as 'not found'."""
        _set_status(dhf, status)
        result = _run(dhf, stage)
        assert result.exit_code == 1
        assert f"already '{status}'" in result.stderr
        assert "not found" not in result.stderr

    def test_a_missing_cr_says_not_found(self, dhf: Path, stage: str) -> None:
        result = _run(dhf, stage, "CR-999")
        assert result.exit_code == 1
        assert "not found" in result.stderr

    def test_a_status_the_lifecycle_does_not_declare_is_reported_as_such(self, dhf: Path, stage: str) -> None:
        _set_status(dhf, "banana")
        result = _run(dhf, stage)
        assert result.exit_code == 1
        assert "banana" in result.stderr and "not a state of a CR" in result.stderr
        assert "not found" not in result.stderr
