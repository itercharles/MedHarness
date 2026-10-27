"""Seeded omissions: one honest change request, and the ways a change can leave something out.

The honest change passes every pre-merge gate. Each omission leaves one thing out of it, the
way an agent might, and the gate whose job it is must stop it. The charter measures the share
of omissions stopped with these (`tests/integration/test_seeded_omissions_are_stopped.py`);
the stopped ones are validation cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from medharness.validation.case import Case, check, invoke
from medharness.validation.project import commit_base, edit, git, item_path, starter

DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup", "test", "regulatory", "security", "usability")
REVIEWED = ["CRS-001", "SRS-001", "SWDD-001", "SYSARCH-001", "RCM-001"]
RISK_ITEMS = ["RCM-001", "RISK-001"]

DOSE = "def dose_cgy(mu: float, factor: float) -> float:\n    return mu * factor\n"
DOSE_TEST = "from dose import dose_cgy\n\n\ndef test_dose():\n    assert dose_cgy(100, 1.0) == 100\n"


def _restore(repo: Path, uid: str) -> None:
    git(repo, "checkout", "main", "--", str(item_path(repo, uid).relative_to(repo)))


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
    edit(repo, "CR-001", **{**fields, **overrides})


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
        data = yaml.safe_load(item_path(repo, uid).read_text(encoding="utf-8"))
        data["id"] = uid.replace("001", "002")
        data["title"] = "Export"
        if uid.startswith("MODULE"):
            data["paths"] = ["src/export.py"]
        else:
            data["module"] = ["MODULE-002"]
        (repo / "DHF" / "items" / directory / f"{data['id']}.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def honest_change(root: Path) -> None:
    """SYS-001 and its test point change with the code, and the CR settles what they reach."""
    starter(root, "Seeded")
    edit(root, "MODULE-001", paths=["src/dose.py", "src/test_dose.py"])
    _module_for_export(root)
    (root / "src").mkdir()
    (root / "src" / "dose.py").write_text(DOSE, encoding="utf-8")
    (root / "src" / "export.py").write_text("def export(plan):\n    return dict(plan)\n", encoding="utf-8")
    (root / "src" / "test_dose.py").write_text(DOSE_TEST, encoding="utf-8")
    commit_base(root)

    edit(root, "SYS-001", content="The dose is scaled by the machine's calibration factor.",
         testing="T1: a calibration factor of 1.02 scales 100 MU to 102 cGy")
    (root / "src" / "dose.py").write_text(DOSE.replace("mu * factor", "mu * factor * calibration()"), encoding="utf-8")
    _honest_cr(root)
    _junit(root, ["CRS-001", "SYS-001", "SRS-001"])


def stopped_by(repo: Path) -> dict[str, list[str]]:
    """The errors of each pre-merge gate that fails, run as CI runs them on a CR's branch."""
    junit = str(repo / "results" / "junit.xml")
    commands = {
        "verify dhf": ["verify", "dhf"],
        "verify tests": ["verify", "tests", "--junit", junit],
        "verify changes": ["verify", "changes", "--cr", "CR-001", "--since-ref", "main", "--code-path", "src"],
        "verify impact": ["verify", "impact", "--cr", "CR-001", "--since-ref", "main"],
        "verify completion": ["verify", "completion", "--cr", "CR-001", "--junit", junit],
    }
    stopped = {}
    for gate, args in commands.items():
        code, answer, _ = invoke(repo, *args)
        check(code == (0 if answer.get("passed") else 1), f"`{gate}` exited {code} with passed={answer.get('passed')}")
        if not answer["passed"]:
            stopped[gate] = answer["errors"]
    return stopped


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
    edit(repo, "UC-001", content="A use case the request never mentioned.")


def declared_item_not_changed(repo: Path) -> None:
    """The CR says SWDD-001 changes; the branch leaves it alone."""
    _honest_cr(repo, affected_items=["SYS-001", "SWDD-001"])


def parent_left_unreviewed(repo: Path) -> None:
    """SRS-001 changes instead of SYS-001; its parent SYS-001 is neither changed nor reviewed."""
    _restore(repo, "SYS-001")
    edit(repo, "SRS-001", content="The dose module applies the calibration factor.", testing="T1: 100 MU at 1.02 gives 102 cGy")
    _honest_cr(repo, affected_items=["SRS-001"], reviewed_items=["SWDD-001"],
               impact_analysis=_analysis(anchors=[{"id": "SRS-001", "evidence": "named in the request"}],
                                         unchanged=[{"id": "SWDD-001", "reason": "still holds"}]))


def changed_requirement_lost_its_test(repo: Path) -> None:
    """The test that verified SYS-001 is gone from the results."""
    _junit(repo, ["CRS-001", "SRS-001"])


def old_test_point_kept(repo: Path) -> None:
    """SYS-001 now requires something new; its test points are what they were."""
    edit(repo, "SYS-001", testing="")


def code_changed_without_a_requirement(repo: Path) -> None:
    """The dose calculation changes; the CR touches no item and claims no impact."""
    _restore(repo, "SYS-001")
    _honest_cr(repo, affected_items=[], reviewed_items=[], affected_risk_items=[],
               impact_analysis=_analysis(anchors=[], unchanged=[]))


def code_changed_outside_the_declared_scope(repo: Path) -> None:
    """Beside the honest change, the export module changes too, and nothing in the DHF says why."""
    (repo / "src" / "export.py").write_text("def export(plan):\n    return {k: v for k, v in plan.items() if v}\n",
                                            encoding="utf-8")


def rejected_to_skip_the_checks(repo: Path) -> None:
    """The CR marks itself rejected, so the export change it never accounted for goes unchecked."""
    code_changed_outside_the_declared_scope(repo)
    _honest_cr(repo, triage_result={"verdict": "rejected", "notes": "duplicate"})


def new_hazard_not_recorded(repo: Path) -> None:
    """The code now rounds the dose; a new way to under-dose, and the risk dimension says not_required."""
    (repo / "src" / "dose.py").write_text(DOSE.replace("mu * factor", "round(mu * factor * calibration())"),
                                          encoding="utf-8")


def verifying_test_weakened(repo: Path) -> None:
    """The test still runs and passes, and no longer checks the dose."""
    (repo / "src" / "test_dose.py").write_text(
        DOSE_TEST.replace("assert dose_cgy(100, 1.0) == 100", "assert True"), encoding="utf-8")


def _the_honest_change_passes(repo: Path) -> None:
    stopped = stopped_by(repo)
    check(stopped == {}, f"the honest change was stopped: {stopped}")


def _stops(omit: Callable[[Path], None], gate: str) -> Callable[[Path], None]:
    def run(repo: Path) -> None:
        omit(repo)
        stopped = stopped_by(repo)
        check(gate in stopped, f"{omit.__name__} ({omit.__doc__}) was not stopped by `{gate}`; "
                               f"stopped by: {sorted(stopped) or 'nothing'}")
    return run


#: (omission, the gate whose job it is, requirement, test point)
STOPPED = [
    (dependent_left_unreviewed, "verify impact", "SRS-007", "T4"),
    (parent_left_unreviewed, "verify impact", "SRS-008", "T2"),
    (risk_control_left_out, "verify impact", "SRS-009", "T2"),
    (code_changed_without_a_requirement, "verify impact", "SRS-010", "T4"),
    (code_changed_outside_the_declared_scope, "verify impact", "SRS-011", "T3"),
    (rejected_to_skip_the_checks, "verify impact", "SRS-012", "T3"),
    (undeclared_item_change, "verify changes", "SRS-030", "T4"),
    (declared_item_not_changed, "verify changes", "SRS-031", "T2"),
]

CASES = [
    Case("the_honest_change_passes_every_gate", "SRS-034", ("T3",), honest_change, _the_honest_change_passes),
    *(Case(omit.__name__, requirement, (point,), honest_change, _stops(omit, gate))
      for omit, gate, requirement, point in STOPPED),
]
