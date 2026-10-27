"""`verify changes`: a branch changes exactly the items its CR lists (SRS-030 to SRS-034).

The seeded project covers SRS-030 T4, SRS-031 T2 and SRS-034 T3.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from medharness.validation.case import Case, check, invoke
from medharness.validation.project import commit_base, edit, item_path, starter


def branch(root: Path) -> None:
    """The starter with some code, committed on `main`, on a branch with nothing changed yet."""
    starter(root, "Changes")
    (root / "src").mkdir()
    (root / "src" / "dose.py").write_text("def dose(mu):\n    return mu\n", encoding="utf-8")
    commit_base(root)


def promised_nothing(root: Path) -> None:
    starter(root, "Changes")
    edit(root, "CR-001", affected_items=[])
    commit_base(root)


def _changes(root: Path, *args: str, since: str = "main") -> tuple[int, dict, str]:
    return invoke(root, "verify", "changes", "--cr", "CR-001", "--since-ref", since, *args)


def _fails(root: Path, *needles: str, args: tuple[str, ...] = ()) -> dict:
    code, answer, _ = _changes(root, *args)
    check(code == 1 and answer["passed"] is False, f"exited {code} with passed={answer['passed']}: {answer['errors']}")
    for needle in needles:
        check(any(needle in e for e in answer["errors"]), f"no error says {needle!r}: {answer['errors']}")
    return answer


def _passes(root: Path, *args: str) -> None:
    code, answer, _ = _changes(root, *args)
    check(code == 0 and answer["passed"] is True and answer["errors"] == [],
          f"exited {code}; errors: {answer['errors']}")


def _copy_as(root: Path, uid: str, new: str) -> None:
    source = item_path(root, uid)
    (source.parent / f"{new}.yaml").write_text(source.read_text(encoding="utf-8").replace(uid, new), encoding="utf-8")


# --- SRS-030: a change the CR does not list ------------------------------------------------------

def unlisted_update(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    edit(root, "UC-001", content="A use case the request never mentioned.")
    _fails(root, "dhf_branch", "UC-001")


def unlisted_create_or_delete(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    _copy_as(root, "SRS-001", "SRS-002")
    _fails(root, "dhf_branch", "SRS-002")
    item_path(root, "SRS-002").unlink()
    item_path(root, "UC-001").unlink()
    _fails(root, "dhf_branch", "UC-001")


def the_cr_need_not_list_itself(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001"], implementation_notes="Scale it.")
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    _passes(root)


# --- SRS-031: a listed item the branch does not change -------------------------------------------

def listed_item_unchanged(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001", "SRS-001"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    _fails(root, "dhf_branch", "SRS-001")


def nothing_listed_nothing_changed(root: Path) -> None:
    _fails(root, "dhf_branch", "lists no affected_items")


# --- SRS-032: --code-path ------------------------------------------------------------------------

def _listed_change(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")


def no_code_change_under_the_path(root: Path) -> None:
    _listed_change(root)
    _fails(root, "code_branch", "src", args=("--code-path", "src"))


def code_change_under_the_path(root: Path) -> None:
    _listed_change(root)
    (root / "src" / "dose.py").write_text("def dose(mu):\n    return mu * 1.02\n", encoding="utf-8")
    _passes(root, "--code-path", "src")


def code_not_checked_without_the_option(root: Path) -> None:
    _listed_change(root)
    _passes(root)


# --- SRS-033: a diff that cannot be read ---------------------------------------------------------

def unreachable_ref_accuses_no_cr(root: Path) -> None:
    for listed in (["SYS-001"], []):
        edit(root, "CR-001", affected_items=listed)
        code, answer, _ = _changes(root, since="origin/main")
        check(code == 1, f"exited {code} with an unreachable ref")
        check(any(e.startswith("diff_unavailable") and "origin/main" in e for e in answer["errors"]),
              f"not reported as diff_unavailable: {answer['errors']}")
        check(not any(e.startswith("dhf_branch") for e in answer["errors"]), f"the CR is accused: {answer['errors']}")


def missing_ref_on_the_command_line(root: Path) -> None:
    _listed_change(root)
    code, answer, stderr = _changes(root, since="no-such-ref")
    check(code == 1 and "no-such-ref" in stderr and any("no-such-ref" in e for e in answer["errors"]),
          f"exited {code}; stderr: {stderr!r}")


ADAPTER = '''from pathlib import Path

from dhfkit.local_adapter import LocalDHFAdapter


class Elsewhere(LocalDHFAdapter):
    tracks_files = False


def make(settings, config, dhf_root):
    return Elsewhere(Path(settings["items"]), config)
'''


def store_that_keeps_no_files(root: Path) -> None:
    """An adapter installed the way a package installs one: a distribution with an entry point."""
    site = root / "site"
    (site / "medharness_validation_elsewhere-1.0.dist-info").mkdir(parents=True)
    (site / "medharness_validation_elsewhere-1.0.dist-info" / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: medharness-validation-elsewhere\nVersion: 1.0\n", encoding="utf-8")
    (site / "medharness_validation_elsewhere-1.0.dist-info" / "entry_points.txt").write_text(
        "[dhfkit.adapters]\nelsewhere = medharness_validation_elsewhere:make\n", encoding="utf-8")
    (site / "medharness_validation_elsewhere.py").write_text(ADAPTER, encoding="utf-8")
    (root / "DHF" / "items").rename(root / "store")
    global_yaml = root / "DHF" / "config" / "global.yaml"
    config = yaml.safe_load(global_yaml.read_text(encoding="utf-8"))
    config["store"] = {"type": "elsewhere", "items": str(root / "store")}
    global_yaml.write_text(yaml.safe_dump(config), encoding="utf-8")
    sys.path.insert(0, str(site))
    try:
        code, answer, stderr = _changes(root)
    finally:
        sys.path.remove(str(site))
        sys.modules.pop("medharness_validation_elsewhere", None)
    said = " ".join(answer.get("errors", [])) + stderr
    check(code == 1 and "elsewhere" in said and "Git" in said, f"exited {code}; said: {said!r}")


# --- SRS-034: exactly the listed changes pass ----------------------------------------------------

def listed_creates_and_updates(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001", "SRS-001", "SRS-002"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    edit(root, "SRS-001", content="The dose module applies the factor.")
    _copy_as(root, "SRS-001", "SRS-002")
    _passes(root)


def a_deletion_counts_as_a_change(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001", "UC-001"])
    edit(root, "SYS-001", content="The dose is scaled by the calibration factor.")
    item_path(root, "UC-001").unlink()
    _passes(root)


CASES = [
    Case("unlisted_update", "SRS-030", ("T1",), branch, unlisted_update),
    Case("unlisted_create_or_delete", "SRS-030", ("T2",), branch, unlisted_create_or_delete),
    Case("the_cr_need_not_list_itself", "SRS-030", ("T3",), branch, the_cr_need_not_list_itself),
    Case("listed_item_unchanged", "SRS-031", ("T1",), branch, listed_item_unchanged),
    Case("nothing_listed_nothing_changed", "SRS-031", ("T3",), promised_nothing, nothing_listed_nothing_changed),
    Case("no_code_change_under_the_path", "SRS-032", ("T1",), branch, no_code_change_under_the_path),
    Case("code_change_under_the_path", "SRS-032", ("T2",), branch, code_change_under_the_path),
    Case("code_not_checked_without_the_option", "SRS-032", ("T3",), branch, code_not_checked_without_the_option),
    Case("unreachable_ref_accuses_no_cr", "SRS-033", ("T1",), branch, unreachable_ref_accuses_no_cr),
    Case("missing_ref_on_the_command_line", "SRS-033", ("T2",), branch, missing_ref_on_the_command_line),
    Case("store_that_keeps_no_files", "SRS-033", ("T3",), branch, store_that_keeps_no_files),
    Case("listed_creates_and_updates", "SRS-034", ("T1",), branch, listed_creates_and_updates),
    Case("a_deletion_counts_as_a_change", "SRS-034", ("T2",), branch, a_deletion_counts_as_a_change),
]
