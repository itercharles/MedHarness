"""`verify impact`: the CR's record settles everything the branch reaches (SRS-007 to SRS-015).

The seeded project covers SRS-007 T4, SRS-008 T2, SRS-009 T2, SRS-010 T4, SRS-011 T3 and SRS-012 T3.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from medharness.validation.case import Case, check, invoke
from medharness.validation.project import commit_base, edit, git, item_path, starter

DIMENSIONS = ("product", "requirements", "architecture", "risk", "soup", "test", "regulatory", "security", "usability")
REVIEWED = ["CRS-001", "SRS-001", "SYSARCH-001", "RCM-001"]


def _analysis(anchors: list[str], unchanged: list[str]) -> dict:
    return {
        "assumptions": ["the request means what it says"],
        "anchors": [{"id": uid, "evidence": "named in the request"} for uid in anchors],
        "unchanged": [{"id": uid, "reason": "still holds"} for uid in unchanged],
        "created": [],
        "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []} for d in DIMENSIONS],
    }


def item_branch(root: Path) -> None:
    """The starter on `main`, and a branch with nothing changed yet."""
    starter(root, "Impact")
    commit_base(root)


def sys_change(root: Path) -> None:
    """SYS-001 changed on the branch, with a CR whose record settles everything it reaches."""
    item_branch(root)
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    edit(root, "CR-001", affected_items=["SYS-001"], reviewed_items=REVIEWED,
         affected_risk_items=["RCM-001", "RISK-001"], impact_analysis=_analysis(["SYS-001"], REVIEWED))


def code_change(root: Path) -> None:
    """MODULE-001 owns src/dose.py; the branch changes that file and nothing in the DHF."""
    starter(root, "Impact")
    edit(root, "MODULE-001", paths=["src/dose.py"])
    (root / "src").mkdir()
    (root / "src" / "dose.py").write_text("DOSE = 1\n", encoding="utf-8")
    commit_base(root)
    (root / "src" / "dose.py").write_text("DOSE = 2\n", encoding="utf-8")
    _review(root, [])


def _review(root: Path, reviewed: list[str]) -> None:
    edit(root, "CR-001", reviewed_items=reviewed, impact_analysis=_analysis([], reviewed))


def _impact(root: Path, cr: str = "CR-001", since: str = "main") -> tuple[int, dict, str]:
    return invoke(root, "verify", "impact", "--cr", cr, "--since-ref", since)


def _fails(root: Path, *needles: str) -> dict:
    code, answer, _ = _impact(root)
    check(code == 1 and answer["passed"] is False, f"exited {code} with passed={answer['passed']}: {answer['errors']}")
    for needle in needles:
        check(any(needle in e for e in answer["errors"]), f"no error says {needle!r}: {answer['errors']}")
    return answer


def _passes(root: Path) -> None:
    code, answer, _ = _impact(root)
    check(code == 0 and answer["passed"] is True and answer["errors"] == [], f"exited {code}; errors: {answer['errors']}")


def _unsettled(answer: dict) -> list[str]:
    return sorted(e.split(":")[0].removeprefix("impact.") for e in answer["errors"] if e.startswith("impact."))


# --- SRS-007: dependents -------------------------------------------------------------------------

def _change_sys_only(root: Path, **cr) -> None:
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    edit(root, "CR-001", affected_items=["SYS-001"], **cr)


def dependents_are_named(root: Path) -> None:
    _change_sys_only(root)
    answer = _fails(root, "SRS-001 depends on SYS-001, which this branch changes")
    check(_unsettled(answer) == ["RCM-001", "SRS-001", "SYSARCH-001"], f"unsettled: {_unsettled(answer)}")


def changed_dependent_reaches_its_own(root: Path) -> None:
    _change_sys_only(root, reviewed_items=["SYSARCH-001", "RCM-001"])
    edit(root, "SRS-001", content="Followed the change.")
    edit(root, "CR-001", affected_items=["SYS-001", "SRS-001"])
    answer = _fails(root)
    check(_unsettled(answer) == ["SWDD-001"], f"unsettled: {_unsettled(answer)}")


def depth_is_configurable(root: Path) -> None:
    _change_sys_only(root, reviewed_items=["SRS-001", "SYSARCH-001", "RCM-001"])
    global_yaml = root / "DHF" / "config" / "global.yaml"
    original = global_yaml.read_text(encoding="utf-8")
    global_yaml.write_text(original + "\nimpact_depth: 2\n", encoding="utf-8")
    deeper = _fails(root)
    check(_unsettled(deeper) == ["SWDD-001"], f"depth 2 reached {_unsettled(deeper)}")
    global_yaml.write_text(original + "\nimpact_depth: 0\n", encoding="utf-8")
    _, off, _ = _impact(root)
    check(_unsettled(off) == [], f"depth 0 reached {_unsettled(off)}")


# --- SRS-008, SRS-009: parents and risk controls -------------------------------------------------

def unsettled_parent(root: Path) -> None:
    git(root, "checkout", "main", "--", str(item_path(root, "SYS-001").relative_to(root)))
    edit(root, "SRS-001", content="The module applies the calibration factor.")
    edit(root, "CR-001", affected_items=["SRS-001"], reviewed_items=["SWDD-001"],
         impact_analysis=_analysis(["SRS-001"], ["SWDD-001"]))
    answer = _fails(root)
    check(any(e.startswith("impact_analysis.parents:") and "SRS-001 changed but its parent SYS-001" in e
              for e in answer["errors"]), f"the parent is not named: {answer['errors']}")


def risk_control_left_out(root: Path) -> None:
    edit(root, "CR-001", affected_risk_items=[])
    _fails(root, "RCM-001 controls SYS-001, which changed, but RCM-001 is not in `affected_risk_items`",
           "RISK-001 is mitigated by RCM-001")


# --- SRS-010, SRS-011: code reaches its module ---------------------------------------------------

def changed_file_reaches_its_module(root: Path) -> None:
    answer = _fails(root)
    check(len(answer["errors"]) == 2 and all(e.startswith("code.src/dose.py: ") for e in answer["errors"]),
          f"errors: {answer['errors']}")
    said = " ".join(answer["errors"])
    check(all(uid in said for uid in ("MODULE-001", "SWDD-001", "SRS-001")), f"errors: {answer['errors']}")


def deleted_file_reaches_its_module(root: Path) -> None:
    (root / "src" / "dose.py").unlink()
    answer = _fails(root)
    check(answer["errors"][0].startswith("code.src/dose.py: "), f"errors: {answer['errors']}")


def _paths_on_main(root: Path, *paths: str) -> None:
    """Change MODULE-001's paths on the base, so the module itself is not a change of the branch."""
    git(root, "stash", "-u", "-q")
    git(root, "checkout", "-q", "main")
    edit(root, "MODULE-001", paths=list(paths))
    git(root, "commit", "-aqm", "paths")
    git(root, "checkout", "-q", "feat")
    git(root, "rebase", "-q", "main")
    git(root, "stash", "pop", "-q")


def directory_and_glob_own_their_files(root: Path) -> None:
    (root / "src" / "export.py").write_text("EXPORT = 1\n", encoding="utf-8")
    _review(root, ["SWDD-001", "SRS-001"])
    _fails(root, "code.src/export.py")
    for paths in (["src/"], ["src/*.py"]):
        _paths_on_main(root, *paths)
        _passes(root)


def unowned_file(root: Path) -> None:
    _review(root, ["SWDD-001", "SRS-001"])
    (root / "src" / "export.py").write_text("EXPORT = 1\n", encoding="utf-8")
    answer = _fails(root)
    check(len(answer["errors"]) == 1 and answer["errors"][0].startswith("code.src/export.py: ")
          and "belongs to no module" in answer["errors"][0], f"errors: {answer['errors']}")


def exemptions_can_be_taken_away(root: Path) -> None:
    _review(root, ["SWDD-001", "SRS-001"])
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    _passes(root)
    global_yaml = root / "DHF" / "config" / "global.yaml"
    global_yaml.write_text(global_yaml.read_text(encoding="utf-8") + "\nunowned_paths: []\n", encoding="utf-8")
    answer = _fails(root)
    check(answer["errors"][0].startswith("code.README.md: ") and "belongs to no module" in answer["errors"][0],
          f"errors: {answer['errors']}")


# --- SRS-012: a CR marked rejected ---------------------------------------------------------------

def _reject(root: Path, *, drop_analysis: bool) -> None:
    path = item_path(root, "CR-001")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if drop_analysis:
        data.pop("impact_analysis", None)
    data["triage_result"] = {"verdict": "rejected", "notes": "duplicate"}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def rejected_cr_changing_items(root: Path) -> None:
    _reject(root, drop_analysis=True)
    answer = _fails(root)
    check(answer["errors"][0].startswith("triage_result:"), f"the first error is not triage_result: {answer['errors']}")
    check(any(e.startswith("impact_analysis") for e in answer["errors"]), f"the missing record is not reported: {answer['errors']}")


def rejected_cr_changing_code(root: Path) -> None:
    _reject(root, drop_analysis=False)
    answer = _fails(root)
    check(answer["errors"][0].startswith("triage_result: ") and any(e.startswith("code.src/dose.py: ") for e in answer["errors"]),
          f"errors: {answer['errors']}")


# --- SRS-013, SRS-014: the record itself, and what cannot be judged ------------------------------

def no_impact_analysis(root: Path) -> None:
    path = item_path(root, "CR-001")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["impact_analysis"]
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    answer = _fails(root)
    check(any(e.startswith("impact_analysis") for e in answer["errors"]), f"errors: {answer['errors']}")


def unsettled_anchor(root: Path) -> None:
    record = _analysis(["SYS-001", "UC-001"], REVIEWED)
    edit(root, "CR-001", impact_analysis=record)
    _fails(root, "anchor UC-001 is neither changed nor in `reviewed_items`")


def cr_not_in_the_dhf(root: Path) -> None:
    code, answer, _ = _impact(root, cr="CR-099")
    check(code == 1 and answer["errors"][0].startswith("cr_item:"), f"exited {code}: {answer['errors']}")


def unreachable_ref(root: Path) -> None:
    code, answer, _ = _impact(root, since="origin/nowhere")
    check(code == 1 and answer["errors"][0].startswith("diff_unavailable:"), f"exited {code}: {answer['errors']}")


# --- SRS-015: a record that settles everything passes --------------------------------------------

def complete_record_passes(root: Path) -> None:
    _passes(root)


def reviewing_dependents_settles_them(root: Path) -> None:
    edit(root, "CR-001", reviewed_items=["CRS-001"], impact_analysis=_analysis(["SYS-001"], ["CRS-001"]))
    _fails(root, "impact.SRS-001")
    edit(root, "CR-001", reviewed_items=REVIEWED, impact_analysis=_analysis(["SYS-001"], REVIEWED))
    _passes(root)


def reviewing_or_changing_what_a_file_reaches(root: Path) -> None:
    _review(root, ["SWDD-001", "SRS-001"])
    _passes(root)
    edit(root, "SWDD-001", content="Applies the new dose constant.")
    edit(root, "SRS-001", content="The dose constant is 2.")
    edit(root, "CR-001", affected_items=["SWDD-001", "SRS-001"])
    _review(root, ["SYS-001", "CRS-001", "SYSARCH-001", "RCM-001"])
    _passes(root)


def docs_ci_and_lockfiles_need_no_module(root: Path) -> None:
    _review(root, ["SWDD-001", "SRS-001"])
    for name in ("README.md", "docs/guide.md", ".github/workflows/ci.yml", "uv.lock", "web/pnpm-lock.yaml"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("changed\n", encoding="utf-8")
    _passes(root)


def rejected_cr_changing_only_itself(root: Path) -> None:
    git(root, "checkout", "main", "--", str(item_path(root, "SYS-001").relative_to(root)))
    _reject(root, drop_analysis=True)
    _passes(root)


def work_on_main_after_the_fork(root: Path) -> None:
    git(root, "commit", "-qam", "branch work")
    git(root, "checkout", "-q", "main")
    edit(root, "UC-001", content="Landed on main.")
    git(root, "commit", "-qam", "main moved on")
    git(root, "checkout", "-q", "feat")
    _passes(root)


CASES = [
    Case("dependents_are_named", "SRS-007", ("T1",), item_branch, dependents_are_named),
    Case("changed_dependent_reaches_its_own", "SRS-007", ("T2",), item_branch, changed_dependent_reaches_its_own),
    Case("depth_is_configurable", "SRS-007", ("T3",), item_branch, depth_is_configurable),
    Case("unsettled_parent", "SRS-008", ("T1",), sys_change, unsettled_parent),
    Case("risk_control_left_out_of_the_record", "SRS-009", ("T1",), sys_change, risk_control_left_out),
    Case("changed_file_reaches_its_module", "SRS-010", ("T1",), code_change, changed_file_reaches_its_module),
    Case("deleted_file_reaches_its_module", "SRS-010", ("T2",), code_change, deleted_file_reaches_its_module),
    Case("directory_and_glob_own_their_files", "SRS-010", ("T3",), code_change, directory_and_glob_own_their_files),
    Case("unowned_file", "SRS-011", ("T1",), code_change, unowned_file),
    Case("exemptions_can_be_taken_away", "SRS-011", ("T2",), code_change, exemptions_can_be_taken_away),
    Case("rejected_cr_changing_items", "SRS-012", ("T1",), sys_change, rejected_cr_changing_items),
    Case("rejected_cr_changing_code", "SRS-012", ("T2",), code_change, rejected_cr_changing_code),
    Case("no_impact_analysis", "SRS-013", ("T1",), sys_change, no_impact_analysis),
    Case("unsettled_anchor", "SRS-013", ("T2",), sys_change, unsettled_anchor),
    Case("cr_not_in_the_dhf_for_impact", "SRS-014", ("T1",), sys_change, cr_not_in_the_dhf),
    Case("unreachable_ref_for_impact", "SRS-014", ("T2",), sys_change, unreachable_ref),
    Case("complete_record_passes", "SRS-015", ("T1",), sys_change, complete_record_passes),
    Case("reviewing_dependents_settles_them", "SRS-015", ("T2",), sys_change, reviewing_dependents_settles_them),
    Case("reviewing_or_changing_what_a_file_reaches", "SRS-015", ("T3",), code_change,
         reviewing_or_changing_what_a_file_reaches),
    Case("docs_ci_and_lockfiles_need_no_module", "SRS-015", ("T4",), code_change, docs_ci_and_lockfiles_need_no_module),
    Case("rejected_cr_changing_only_itself", "SRS-015", ("T5",), sys_change, rejected_cr_changing_only_itself),
    Case("work_on_main_after_the_fork", "SRS-015", ("T6",), sys_change, work_on_main_after_the_fork),
]
