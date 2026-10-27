"""`verify completion`: a CR closes only on a complete record whose changed items are verified (SRS-002 to SRS-006)."""

from __future__ import annotations

from pathlib import Path

import yaml

from dhfkit.paths import DEFAULTS_DIR
from medharness.validation.case import Case, check, invoke
from medharness.validation.project import edit, item_path, junit, scaffolded, starter

RECORD = {"affected_items": [], "implementation_notes": "Scale the dose by the calibration factor.",
          "affected_risk_items": []}


def verified_starter(root: Path) -> None:
    starter(root, "Completion")
    edit(root, "CR-001", **RECORD)


def _completion(root: Path, *junit_paths: Path) -> tuple[int, dict, str]:
    args = ["verify", "completion", "--cr", "CR-001"]
    for path in junit_paths:
        args += ["--junit", str(path)]
    return invoke(root, *args)


def _refused(root: Path, *needles: str, junit_paths: tuple[Path, ...] = ()) -> dict:
    code, answer, _ = _completion(root, *junit_paths)
    check(code == 1 and answer["passed"] is False, f"exited {code} with passed={answer['passed']}: {answer['errors']}")
    for needle in needles:
        check(any(needle in e for e in answer["errors"]), f"no error names {needle!r}: {answer['errors']}")
    return answer


def _closes(root: Path, *junit_paths: Path) -> dict:
    code, answer, _ = _completion(root, *junit_paths)
    check(code == 0 and answer["passed"] is True, f"exited {code}; errors: {answer['errors']}")
    return answer


def _without(root: Path, uid: str, field: str) -> None:
    path = item_path(root, uid)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.pop(field, None)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _results(root: Path, *tests: tuple) -> Path:
    return junit(root / "results" / "case.xml", *tests)


# --- SRS-002: the CR's own record ----------------------------------------------------------------

def cr_not_in_the_dhf(root: Path) -> None:
    item_path(root, "CR-001").unlink()
    _refused(root, "CR-001")


def affected_items_not_recorded(root: Path) -> None:
    _without(root, "CR-001", "affected_items")
    _refused(root, "affected_items")


def implementation_notes_missing_or_empty(root: Path) -> None:
    _without(root, "CR-001", "implementation_notes")
    _refused(root, "implementation_notes")
    edit(root, "CR-001", implementation_notes="")
    _refused(root, "implementation_notes")


def affected_risk_items_missing_or_null(root: Path) -> None:
    _without(root, "CR-001", "affected_risk_items")
    _refused(root, "affected_risk_items")
    edit(root, "CR-001", affected_risk_items=None)
    _refused(root, "affected_risk_items")


def closure_asks_what_the_cr_type_asks(root: Path) -> None:
    cr_type = yaml.safe_load((DEFAULTS_DIR / "config" / "doc_types" / "cr.yaml").read_text(encoding="utf-8"))
    to_completed = next(t for t in cr_type["lifecycle"]["transitions"] if t["to_state"] == "completed")
    to_completed["criteria"].append({"id": "described", "name": "Description written", "check_type": "field_not_empty",
                                     "field": "description", "required": True})
    override = root / "DHF" / "config" / "doc_types" / "cr.yaml"
    override.parent.mkdir(exist_ok=True)
    override.write_text(yaml.safe_dump(cr_type), encoding="utf-8")
    _without(root, "CR-001", "description")
    _refused(root, "Description written")

    to_completed["criteria"] = []
    override.write_text(yaml.safe_dump(cr_type), encoding="utf-8")
    for field in RECORD:
        _without(root, "CR-001", field)
    _closes(root)


def every_incomplete_field_on_the_command_line(root: Path) -> None:
    for field in RECORD:
        _without(root, "CR-001", field)
    code, answer, stderr = _completion(root)
    check(code != 0, f"exited {code}")
    for field in RECORD:
        check(any(field in e for e in answer["errors"]), f"{field} is not reported: {answer['errors']}")
        check(f"FAIL [completion]" in stderr and field in stderr, f"stderr does not report {field}: {stderr!r}")


# --- SRS-003: an affected item absent from the DHF -----------------------------------------------

def affected_item_absent(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-404"])
    answer = _refused(root, "SRS-404")
    check(any("absent from the DHF" in e or "not in the DHF" in e for e in answer["errors"]),
          f"the error does not say SRS-404 is absent: {answer['errors']}")


def absent_item_on_the_command_line(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-404"])
    code, _, stderr = _completion(root)
    check(code != 0 and "SRS-404" in stderr, f"exited {code}; stderr: {stderr!r}")


# --- SRS-004: a changed requirement with no verification method ----------------------------------

def requirement_without_a_method(root: Path) -> None:
    _without(root, "SRS-001", "verification_method")
    edit(root, "CR-001", affected_items=["SRS-001"])
    _refused(root, "SRS-001", "verification_method", junit_paths=(root / "results" / "junit.xml",))


HWR = {
    "code": "HWR", "name": "Hardware Requirement", "prefix": "HWR-", "directory": "hwr",
    "role": "hardware_requirement",
    "properties": ["id", {"name": "title", "format": "short_text", "label": "Title"},
                   {"name": "verification_method", "format": "multiselect", "label": "Verification Method",
                    "options": ["Test", "Inspection", "Analysis", "Demonstration"]}],
}


def added_type_without_a_method(root: Path) -> None:
    (root / "DHF" / "config" / "doc_types").mkdir(exist_ok=True)
    (root / "DHF" / "config" / "doc_types" / "hwr.yaml").write_text(yaml.safe_dump(HWR), encoding="utf-8")
    (root / "DHF" / "items" / "hwr").mkdir()
    (root / "DHF" / "items" / "hwr" / "HWR-001.yaml").write_text(
        yaml.safe_dump({"id": "HWR-001", "title": "Battery runs 8 hours"}), encoding="utf-8")
    edit(root, "CR-001", affected_items=["HWR-001"])
    _refused(root, "HWR-001")


def scaffolded_requirement_without_a_method(root: Path) -> None:
    edit(root, "CR-001", **{**RECORD, "affected_items": ["SRS-001"]})
    _refused(root, "SRS-001", "verification_method")


# --- SRS-005: Test declared, no passing JUnit evidence -------------------------------------------

def no_linked_test(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001"])
    _refused(root, "SRS-001", junit_paths=(_results(root, ("test_other", "SYS-001", "passed")),))


def no_junit_at_all(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001"])
    _refused(root, "SRS-001")


def the_only_linked_test_failed(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001"])
    _refused(root, "SRS-001", junit_paths=(_results(root, ("test_it", "SRS-001", "failed")),))


def a_failing_test_outweighs_a_passing_one(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001"])
    _refused(root, "SRS-001", junit_paths=(_results(root, ("test_ok", "SRS-001", "passed"), ("test_bad", "SRS-001", "failed")),))


# --- SRS-006: a complete, verified CR closes, blamed for nothing else ----------------------------

def verified_items_close(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SYS-001", "SRS-001"])
    _closes(root, _results(root, ("test_sys", "SYS-001", "passed"), ("test_srs", "SRS-001", "passed")))


def nothing_affected_closes(root: Path) -> None:
    _closes(root)


def inspection_and_risk_items_need_no_test(root: Path) -> None:
    edit(root, "SRS-001", verification_method=["Inspection"])
    edit(root, "CR-001", affected_items=["SRS-001", "RISK-001"])
    _closes(root, _results(root, ("test_other", "SYS-001", "passed")))


def an_unlisted_item_is_not_the_crs(root: Path) -> None:
    _without(root, "SYS-001", "verification_method")
    edit(root, "CR-001", affected_items=["SRS-001"])
    _closes(root, _results(root, ("test_srs", "SRS-001", "passed")))


def a_changed_soup_item_needs_no_method(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SOUP-001"])
    _closes(root)


def closing_on_the_command_line(root: Path) -> None:
    code, answer, _ = _completion(root)
    check(code == 0 and "CR-001" in answer["summary"], f"exited {code}; summary: {answer['summary']!r}")


def a_name_tag_counts_as_evidence(root: Path) -> None:
    edit(root, "CR-001", affected_items=["SRS-001"])
    _closes(root, _results(root, ("test_it @links:SRS-001", None, "passed")))


def scaffolded_with_a_record(root: Path) -> None:
    scaffolded(root, "Completion")


CASES = [
    Case("cr_not_in_the_dhf", "SRS-002", ("T1",), verified_starter, cr_not_in_the_dhf, tools=()),
    Case("affected_items_not_recorded", "SRS-002", ("T2",), verified_starter, affected_items_not_recorded, tools=()),
    Case("implementation_notes_missing_or_empty", "SRS-002", ("T3",), verified_starter,
         implementation_notes_missing_or_empty, tools=()),
    Case("affected_risk_items_missing_or_null", "SRS-002", ("T4",), verified_starter,
         affected_risk_items_missing_or_null, tools=()),
    Case("closure_asks_what_the_cr_type_asks", "SRS-002", ("T5",), verified_starter,
         closure_asks_what_the_cr_type_asks, tools=()),
    Case("every_incomplete_field_on_the_command_line", "SRS-002", ("T6",), verified_starter,
         every_incomplete_field_on_the_command_line, tools=()),
    Case("affected_item_absent", "SRS-003", ("T1",), verified_starter, affected_item_absent, tools=()),
    Case("absent_item_on_the_command_line", "SRS-003", ("T2",), verified_starter, absent_item_on_the_command_line, tools=()),
    Case("requirement_without_a_method", "SRS-004", ("T1",), verified_starter, requirement_without_a_method, tools=()),
    Case("added_type_without_a_method", "SRS-004", ("T2",), verified_starter, added_type_without_a_method, tools=()),
    Case("scaffolded_requirement_without_a_method", "SRS-004", ("T3",), scaffolded_with_a_record,
         scaffolded_requirement_without_a_method, tools=()),
    Case("no_linked_test", "SRS-005", ("T1",), verified_starter, no_linked_test, tools=()),
    Case("no_junit_at_all", "SRS-005", ("T2",), verified_starter, no_junit_at_all, tools=()),
    Case("the_only_linked_test_failed", "SRS-005", ("T3",), verified_starter, the_only_linked_test_failed, tools=()),
    Case("a_failing_test_outweighs_a_passing_one", "SRS-005", ("T4",), verified_starter,
         a_failing_test_outweighs_a_passing_one, tools=()),
    Case("verified_items_close", "SRS-006", ("T1",), verified_starter, verified_items_close, tools=()),
    Case("nothing_affected_closes", "SRS-006", ("T2",), verified_starter, nothing_affected_closes, tools=()),
    Case("inspection_and_risk_items_need_no_test", "SRS-006", ("T3",), verified_starter,
         inspection_and_risk_items_need_no_test, tools=()),
    Case("an_unlisted_item_is_not_the_crs", "SRS-006", ("T4",), verified_starter, an_unlisted_item_is_not_the_crs, tools=()),
    Case("a_changed_soup_item_needs_no_method", "SRS-006", ("T5",), verified_starter,
         a_changed_soup_item_needs_no_method, tools=()),
    Case("closing_on_the_command_line", "SRS-006", ("T6",), verified_starter, closing_on_the_command_line, tools=()),
    Case("a_name_tag_counts_as_evidence", "SRS-006", ("T7",), verified_starter, a_name_tag_counts_as_evidence, tools=()),
]
