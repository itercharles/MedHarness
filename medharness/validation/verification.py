"""`verify tests`: every requirement and declared test point needs a passing test (SRS-024 to SRS-029).

The starter's requirements are CRS-001, SYS-001 and SRS-001, each declaring Test.
"""

from __future__ import annotations

from pathlib import Path

from medharness.validation.case import Case, check, invoke
from medharness.validation.project import edit, junit, starter

OTHERS = "CRS-001,SYS-001"
ALL = f"{OTHERS},SRS-001"


def verified_starter(root: Path) -> None:
    starter(root, "Verification")


def _tests(root: Path, *tests: tuple, strict: bool = False) -> tuple[int, dict, str]:
    args = ["verify", "tests", "--junit", str(junit(root / "results" / "case.xml", *tests))]
    return invoke(root, *args, *(["--strict"] if strict else []))


def _fails(answer: tuple[int, dict, str], *needles: str) -> None:
    code, result, _ = answer
    check(code == 1 and result["passed"] is False, f"exited {code} with passed={result['passed']}: {result['errors']}")
    for needle in needles:
        check(any(needle in e for e in result["errors"]), f"no error says {needle!r}: {result['errors']}")


def _passes(answer: tuple[int, dict, str]) -> dict:
    code, result, _ = answer
    check(code == 0 and result["passed"] is True and result["errors"] == [], f"exited {code}; errors: {result['errors']}")
    return result


def _warns(result: dict, needle: str) -> None:
    check(any(needle in w for w in result["warnings"]), f"no warning says {needle!r}: {result['warnings']}")


# --- SRS-024: a requirement no passing test covers -----------------------------------------------

def requirement_with_no_linked_test(root: Path) -> None:
    _fails(_tests(root, ("test_others", OTHERS, "passed")), "SRS: 0/1 requirements covered", "SRS-001")


def failed_or_errored_test_is_not_evidence(root: Path) -> None:
    for outcome in ("failed", "error"):
        _fails(_tests(root, ("test_others", OTHERS, "passed"), ("test_srs", "SRS-001", outcome)), "SRS-001")


def skipped_test_is_not_evidence(root: Path) -> None:
    _fails(_tests(root, ("test_others", OTHERS, "passed"), ("test_srs", "SRS-001", "skipped")), "SRS-001")


def failing_test_outweighs_a_passing_one(root: Path) -> None:
    _fails(_tests(root, ("test_all", ALL, "passed"), ("test_srs", "SRS-001", "failed")), "SRS-001")


def no_junit_given(root: Path) -> None:
    code, result, _ = invoke(root, "verify", "tests")
    _fails((code, result, ""), "--junit")


# --- SRS-025: a declared test point no passing test covers ---------------------------------------

def with_two_points(root: Path) -> None:
    starter(root, "Verification")
    edit(root, "SRS-001", testing="T1: a short password is refused\nT2: a long one is accepted")


def uncovered_point(root: Path) -> None:
    _fails(_tests(root, ("test_all", ALL, "passed", "T1")), "SRS-001: test points T2 uncovered")


def failing_test_covers_no_point(root: Path) -> None:
    _fails(_tests(root, ("test_all", ALL, "passed", "T1"), ("test_t2", "SRS-001", "failed", "T2")), "T2 uncovered")


def points_across_separate_tests(root: Path) -> None:
    _passes(_tests(root, ("test_all", ALL, "passed", "T1"), ("test_t2", "SRS-001", "passed", "T2")))


def point_on_one_requirement_covers_no_other(root: Path) -> None:
    edit(root, "SYS-001", testing="T1: the system does it\nT2: and undoes it")
    _fails(_tests(root, ("test_all", ALL, "passed", "T1"), ("test_srs_t2", "SRS-001", "passed", "T2")),
           "SYS-001: test points T2 uncovered")


# --- SRS-026: no verification_method declared ----------------------------------------------------

def no_method_fails_under_strict(root: Path) -> None:
    edit(root, "SRS-001", verification_method=[])
    _fails(_tests(root, ("test_all", ALL, "passed"), strict=True), "SRS-001: no verification_method declared")


def no_method_warns_without_strict(root: Path) -> None:
    edit(root, "SRS-001", verification_method=[])
    _warns(_passes(_tests(root, ("test_all", ALL, "passed"))), "SRS-001: no verification_method declared")


def no_method_reported_without_junit(root: Path) -> None:
    edit(root, "SRS-001", verification_method=[])
    code, result, _ = invoke(root, "verify", "tests")
    check(code == 1, f"exited {code}")
    _warns(result, "SRS-001: no verification_method declared")


# --- SRS-027: Inspection, Analysis, Demonstration await sign-off ---------------------------------

def inspection_needs_no_test(root: Path) -> None:
    edit(root, "SRS-001", verification_method=["Inspection"])
    _warns(_passes(_tests(root, ("test_others", OTHERS, "passed"))), "SRS-001: verified by Inspection")


def test_and_inspection_still_need_a_test(root: Path) -> None:
    edit(root, "SRS-001", verification_method=["Test", "Inspection"])
    _fails(_tests(root, ("test_others", OTHERS, "passed")), "SRS-001")


def inspection_is_not_counted_as_covered(root: Path) -> None:
    edit(root, "SRS-001", verification_method=["Inspection"])
    result = _passes(_tests(root, ("test_others", OTHERS, "passed")))
    check(result["summary"].startswith("2/2 "), f"the Inspection requirement is counted: {result['summary']!r}")


# --- SRS-028: a link to an item the DHF does not have --------------------------------------------

def unknown_link_warns(root: Path) -> None:
    _warns(_passes(_tests(root, ("test_all", f"{ALL},SRS-999", "passed"))), "SRS-999: linked by 'test_all' but not in the DHF")


def unknown_link_fails_under_strict(root: Path) -> None:
    _fails(_tests(root, ("test_all", f"{ALL},SRS-999", "passed"), strict=True), "SRS-999: linked by 'test_all'")


# --- SRS-029: everything covered passes ----------------------------------------------------------

def every_requirement_covered(root: Path) -> None:
    result = _passes(_tests(root, ("test_all", ALL, "passed")))
    check(result["summary"].startswith("3/3 "), f"summary: {result['summary']!r}")


def every_point_covered(root: Path) -> None:
    _passes(_tests(root, ("test_t1", ALL, "passed", "T1"), ("test_t2", "SRS-001", "passed", "T2")))


def name_tags_count_as_properties_do(root: Path) -> None:
    _passes(_tests(root, ("test_others", OTHERS, "passed"),
                   ("test_short @links:SRS-001 @testing:T1", None, "passed"),
                   ("test_long @links:SRS-001 @testing:T2", None, "passed")))


CASES = [
    Case("requirement_with_no_linked_test", "SRS-024", ("T1",), verified_starter, requirement_with_no_linked_test, tools=()),
    Case("failed_or_errored_test_is_not_evidence", "SRS-024", ("T2",), verified_starter,
         failed_or_errored_test_is_not_evidence, tools=()),
    Case("skipped_test_is_not_evidence", "SRS-024", ("T3",), verified_starter, skipped_test_is_not_evidence, tools=()),
    Case("failing_test_outweighs_a_passing_one", "SRS-024", ("T4",), verified_starter,
         failing_test_outweighs_a_passing_one, tools=()),
    Case("no_junit_given", "SRS-024", ("T5",), verified_starter, no_junit_given, tools=()),
    Case("uncovered_point", "SRS-025", ("T1",), with_two_points, uncovered_point, tools=()),
    Case("failing_test_covers_no_point", "SRS-025", ("T2",), with_two_points, failing_test_covers_no_point, tools=()),
    Case("points_across_separate_tests", "SRS-025", ("T3",), with_two_points, points_across_separate_tests, tools=()),
    Case("point_on_one_requirement_covers_no_other", "SRS-025", ("T4",), with_two_points,
         point_on_one_requirement_covers_no_other, tools=()),
    Case("no_method_fails_under_strict", "SRS-026", ("T1",), verified_starter, no_method_fails_under_strict, tools=()),
    Case("no_method_warns_without_strict", "SRS-026", ("T2",), verified_starter, no_method_warns_without_strict, tools=()),
    Case("no_method_reported_without_junit", "SRS-026", ("T3",), verified_starter, no_method_reported_without_junit, tools=()),
    Case("inspection_needs_no_test", "SRS-027", ("T1",), verified_starter, inspection_needs_no_test, tools=()),
    Case("test_and_inspection_still_need_a_test", "SRS-027", ("T2",), verified_starter,
         test_and_inspection_still_need_a_test, tools=()),
    Case("inspection_is_not_counted_as_covered", "SRS-027", ("T3",), verified_starter,
         inspection_is_not_counted_as_covered, tools=()),
    Case("unknown_link_warns", "SRS-028", ("T1",), verified_starter, unknown_link_warns, tools=()),
    Case("unknown_link_fails_under_strict", "SRS-028", ("T2",), verified_starter, unknown_link_fails_under_strict, tools=()),
    Case("every_requirement_covered", "SRS-029", ("T1",), verified_starter, every_requirement_covered, tools=()),
    Case("every_point_covered", "SRS-029", ("T2",), with_two_points, every_point_covered, tools=()),
    Case("name_tags_count_as_properties_do", "SRS-029", ("T3",), with_two_points, name_tags_count_as_properties_do, tools=()),
]
