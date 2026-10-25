"""Seeded omissions: how many of the ways a change request can leave something out the gates stop.

The charter's first measure. One honest change request passes every pre-merge gate; each case
leaves one thing out of it, the way an agent might. A case is stopped when any gate exits non-zero.
Omissions the gates do not stop today are `xfail(strict=True)` with the charter gap they belong to,
so the summary line (passed, xfailed) is the catch rate, and closing a gap turns its cases into
failures until they are moved to the stopped side.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

import pytest
import yaml
from click.testing import CliRunner
from fixtures.starter import keep_the_starter_text, verify_the_starter

from medharness.cli import main
from medharness.scaffold import replace_placeholders, scaffold_dhf

DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup", "test", "regulatory", "security", "usability")
REVIEWED = ["CRS-001", "SRS-001", "SWDD-001", "SYSARCH-001", "RCM-001"]
RISK_ITEMS = ["RCM-001", "RISK-001"]

DOSE = "def dose_cgy(mu: float, factor: float) -> float:\n    return mu * factor\n"
DOSE_TEST = "from dose import dose_cgy\n\n\ndef test_dose():\n    assert dose_cgy(100, 1.0) == 100\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _item(repo: Path, uid: str) -> Path:
    return next((repo / "DHF" / "items").rglob(f"{uid}.yaml"))


def _edit(repo: Path, uid: str, **fields) -> None:
    path = _item(repo, uid)
    data = yaml.safe_load(path.read_text())
    data.update(fields)
    path.write_text(yaml.safe_dump(data))


def _restore(repo: Path, uid: str) -> None:
    _git(repo, "checkout", "main", "--", str(_item(repo, uid).relative_to(repo)))


def _analysis(**overrides) -> dict:
    record = {
        "assumptions": ["the request means what it says"],
        "anchors": [{"id": "SYS-001", "evidence": "named in the request"}],
        "unchanged": [{"id": uid, "reason": "still holds after the change"} for uid in REVIEWED],
        "created": [],
        "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []}
                       for d in DIMENSIONS],
    }
    return {**record, **overrides}


def _honest_cr(repo: Path, **overrides) -> None:
    fields = {
        "affected_items": ["SYS-001"],
        "reviewed_items": REVIEWED,
        "affected_risk_items": RISK_ITEMS,
        "impact_analysis": _analysis(),
        "implementation_notes": "Scale the dose by the calibration factor.",
    }
    _edit(repo, "CR-001", **{**fields, **overrides})


def _junit(repo: Path, ids: list[str]) -> Path:
    junit = repo / "results" / "junit.xml"
    junit.write_text(
        '<testsuite name="s"><testcase classname="c" name="test_dose">'
        f'<properties><property name="medharness.links" value="{",".join(ids)}"/>'
        '<property name="medharness.testing" value="T1"/></properties>'
        "</testcase></testsuite>", encoding="utf-8")
    return junit


def _module_for_export(repo: Path) -> None:
    """A second module, with its own design item, that owns the export code."""
    for uid, directory in (("MODULE-001", "04_modules"), ("SWDD-001", "05_swdd")):
        data = yaml.safe_load(_item(repo, uid).read_text())
        data["id"] = uid.replace("001", "002")
        data["title"] = "Export"
        if uid.startswith("MODULE"):
            data["paths"] = ["src/export.py"]
        else:
            data["module"] = ["MODULE-002"]
        (repo / "DHF" / "items" / directory / f"{data['id']}.yaml").write_text(yaml.safe_dump(data))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """The honest change: SYS-001 and its test point change with the code, and the CR settles what they reach."""
    scaffold_dhf(tmp_path)
    replace_placeholders(tmp_path, "Seeded")
    keep_the_starter_text(tmp_path / "DHF")
    verify_the_starter(tmp_path / "DHF", tmp_path / "results")
    (tmp_path / ".gitignore").write_text("results/\n")
    _edit(tmp_path, "MODULE-001", paths=["src/dose.py", "src/test_dose.py"])
    _module_for_export(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dose.py").write_text(DOSE)
    (tmp_path / "src" / "export.py").write_text("def export(plan):\n    return dict(plan)\n")
    (tmp_path / "src" / "test_dose.py").write_text(DOSE_TEST)
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat")

    _edit(tmp_path, "SYS-001", content="The dose is scaled by the machine's calibration factor.",
          testing="T1: a calibration factor of 1.02 scales 100 MU to 102 cGy")
    (tmp_path / "src" / "dose.py").write_text(DOSE.replace("mu * factor", "mu * factor * calibration()"))
    _honest_cr(tmp_path)
    _junit(tmp_path, ["CRS-001", "SYS-001", "SRS-001"])
    return tmp_path


def _gates(repo: Path) -> dict[str, dict]:
    """Every pre-merge gate, as CI runs them on a change request's branch."""
    junit = str(repo / "results" / "junit.xml")
    commands = {
        "verify dhf": ["verify", "dhf"],
        "verify tests": ["verify", "tests", "--junit", junit],
        "verify changes": ["verify", "changes", "--cr", "CR-001", "--since-ref", "main", "--code-path", "src"],
        "verify impact": ["verify", "impact", "--cr", "CR-001", "--since-ref", "main"],
        "verify completion": ["verify", "completion", "--cr", "CR-001", "--junit", junit],
    }
    answers = {}
    for gate, args in commands.items():
        result = CliRunner().invoke(main, ["--dhf", str(repo / "DHF"), *args])
        assert "Traceback" not in (result.stderr or ""), result.stderr
        answers[gate] = json.loads(result.stdout.splitlines()[0])
    return answers


def _stopped_by(repo: Path) -> dict[str, list[str]]:
    return {gate: answer["errors"] for gate, answer in _gates(repo).items() if not answer["passed"]}


def test_the_honest_change_passes_every_gate(repo: Path) -> None:
    """The control: without it, a case 'stopped' by a fixture the gates reject anyway would count as caught."""
    assert _stopped_by(repo) == {}


# --- omissions -------------------------------------------------------------------------------------

def dependent_left_unreviewed(repo: Path) -> None:
    """SRS-001 derives from the changed SYS-001; nobody looked at it."""
    kept = [uid for uid in REVIEWED if uid != "SRS-001"]
    _honest_cr(repo, reviewed_items=kept,
               impact_analysis=_analysis(unchanged=[{"id": uid, "reason": "still holds"} for uid in kept]))


def risk_control_left_out(repo: Path) -> None:
    """RCM-001 controls the changed SYS-001; the CR records no risk impact."""
    _honest_cr(repo, affected_risk_items=[])


def undeclared_item_change(repo: Path) -> None:
    """The branch also rewrites UC-001, and the CR does not say so."""
    _edit(repo, "UC-001", content="A use case the request never mentioned.")


def declared_item_not_changed(repo: Path) -> None:
    """The CR says SWDD-001 changes; the branch leaves it alone."""
    _honest_cr(repo, affected_items=["SYS-001", "SWDD-001"])


def parent_left_unreviewed(repo: Path) -> None:
    """SRS-001 changes instead of SYS-001; its parent SYS-001 is neither changed nor reviewed."""
    _restore(repo, "SYS-001")
    _edit(repo, "SRS-001", content="The dose module applies the calibration factor.", testing="T1: 100 MU at 1.02 gives 102 cGy")
    _honest_cr(repo, affected_items=["SRS-001"], reviewed_items=["SWDD-001"],
               impact_analysis=_analysis(anchors=[{"id": "SRS-001", "evidence": "named in the request"}],
                                         unchanged=[{"id": "SWDD-001", "reason": "still holds"}]))


def changed_requirement_lost_its_test(repo: Path) -> None:
    """The test that verified SYS-001 is gone from the results."""
    _junit(repo, ["CRS-001", "SRS-001"])


def old_test_point_kept(repo: Path) -> None:
    """SYS-001 now requires something new; its test points are what they were."""
    _edit(repo, "SYS-001", testing="")


def code_changed_without_a_requirement(repo: Path) -> None:
    """The dose calculation changes; the CR touches no item and claims no impact."""
    _restore(repo, "SYS-001")
    _honest_cr(repo, affected_items=[], reviewed_items=[], affected_risk_items=[],
               impact_analysis=_analysis(anchors=[], unchanged=[]))


def code_changed_outside_the_declared_scope(repo: Path) -> None:
    """Beside the honest change, the export module changes too, and nothing in the DHF says why."""
    (repo / "src" / "export.py").write_text("def export(plan):\n    return {k: v for k, v in plan.items() if v}\n")


def rejected_to_skip_the_checks(repo: Path) -> None:
    """The CR marks itself rejected, so the export change it never accounted for goes unchecked."""
    code_changed_outside_the_declared_scope(repo)
    _honest_cr(repo, triage_result={"verdict": "rejected", "notes": "duplicate"})


def new_hazard_not_recorded(repo: Path) -> None:
    """The code now rounds the dose; a new way to under-dose, and the risk dimension says not_required."""
    (repo / "src" / "dose.py").write_text(DOSE.replace("mu * factor", "round(mu * factor * calibration())"))


def verifying_test_weakened(repo: Path) -> None:
    """The test still runs and passes, and no longer checks the dose."""
    (repo / "src" / "test_dose.py").write_text(DOSE_TEST.replace("assert dose_cgy(100, 1.0) == 100", "assert True"))


def _missed(gap: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{gap}: {why}")


OMISSIONS: list = [
    pytest.param(dependent_left_unreviewed, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-007"), pytest.mark.dhf_testing("T4")]),
    pytest.param(risk_control_left_out, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-009"), pytest.mark.dhf_testing("T2")]),
    pytest.param(undeclared_item_change, "verify changes"),
    pytest.param(declared_item_not_changed, "verify changes"),
    pytest.param(parent_left_unreviewed, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-008"), pytest.mark.dhf_testing("T2")]),
    pytest.param(changed_requirement_lost_its_test, "verify tests"),
    pytest.param(old_test_point_kept, None, marks=_missed("warning", "test_points_unchanged warns, it does not stop")),
    pytest.param(code_changed_without_a_requirement, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-010"), pytest.mark.dhf_testing("T4")]),
    pytest.param(code_changed_outside_the_declared_scope, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-011"), pytest.mark.dhf_testing("T3")]),
    pytest.param(rejected_to_skip_the_checks, "verify impact",
                marks=[pytest.mark.dhf_links("SRS-012"), pytest.mark.dhf_testing("T3")]),
    pytest.param(new_hazard_not_recorded, None, marks=_missed("G2", "a hazard linked to nothing has no way in")),
    pytest.param(verifying_test_weakened, None, marks=_missed("adequacy", "a passing test is taken at its word")),
]


@pytest.mark.parametrize(("omit", "gate"), OMISSIONS, ids=[p.values[0].__name__ for p in OMISSIONS])
def test_a_seeded_omission_is_stopped(repo: Path, omit: Callable[[Path], None], gate: str | None) -> None:
    """Stopped by the gate whose job it is, not by a side effect of the seeding; a known miss by any gate at all."""
    omit(repo)
    stopped = _stopped_by(repo)
    assert stopped, f"{omit.__name__} passed every gate: {omit.__doc__}"
    assert gate is None or gate in stopped, f"{omit.__name__} was stopped by {sorted(stopped)}, not {gate}"
