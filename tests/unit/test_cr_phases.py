"""Which CRs `build plan` and `build code` will work on.

`build plan` needs the CR to exist; `build code` also needs a plan to implement, the CR's
`implementation_notes`. The CR's state is the project's to move: the stages neither read nor change it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from dhfkit.store import open_store
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


def test_the_scaffolded_cr_can_be_planned(dhf: Path) -> None:
    """The documented first command must work on a fresh project."""
    assert _run(dhf, "plan").exit_code == 0


@pytest.mark.parametrize("status", [None, "new", "design", "develop", "completed", "rejected", "cancelled"])
def test_the_state_of_the_cr_is_not_looked_at(dhf: Path, status) -> None:
    _set_status(dhf, status)
    assert _run(dhf, "plan").exit_code == 0
    open_store(dhf).update_item("CR-001", {"implementation_notes": "Plan."})
    assert _run(dhf, "code").exit_code == 0


def test_code_needs_a_plan_to_implement(dhf: Path) -> None:
    result = _run(dhf, "code")
    assert result.exit_code == 1
    assert "no implementation_notes" in result.stderr and "build plan --cr CR-001" in result.stderr


@pytest.mark.parametrize("stage", ["plan", "code"])
def test_a_missing_cr_says_not_found(dhf: Path, stage: str) -> None:
    result = _run(dhf, stage, "CR-999")
    assert result.exit_code == 1
    assert "not found" in result.stderr
