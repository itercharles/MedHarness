"""`build validation` judges the set it runs: only every point passing, on a checked release, passes.

These run the command in this checkout, an editable install with no release record, so the
result here is never `passed`; `test_a_released_wheel_validates_itself.py` runs a built wheel.
The set is replaced with small cases to reach each verdict quickly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.results import ValidationReport
from medharness.services import validation
from medharness.validation.case import Case, check


def _nothing(root: Path) -> None:
    (root / "built").write_text("", encoding="utf-8")


def _passes(root: Path) -> None:
    check((root / "built").is_file(), "the case did not get a copy of its project")


def _fails(root: Path) -> None:
    check(False, "the gate let the omission through")


def _crashes(root: Path) -> None:
    raise KeyError("errors")


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cases: list[Case], *args: str):
    monkeypatch.setattr(validation, "CASES", cases)
    out = tmp_path / "report"
    result = CliRunner().invoke(main, ["build", "validation", "--out-dir", str(out), *args])
    report = json.loads(result.stdout)
    ValidationReport.model_validate(report)
    return result, report, out


def _points(report: dict) -> dict[str, tuple[str, str]]:
    return {f"{r['id']} {p['id']}": (p["status"], p["message"]) for r in report["requirements"] for p in r["points"]}


@pytest.mark.dhf_links("SRS-072")
@pytest.mark.dhf_testing("T2")
def test_every_point_passing_on_a_build_without_a_release_record_is_incomplete(tmp_path, monkeypatch) -> None:
    result, report, out = _run(tmp_path, monkeypatch, [Case("a", "SRS-034", ("T3",), _nothing, _passes, tools=())])
    assert result.exit_code == 1
    assert report["result"] == "incomplete"
    assert _points(report) == {"SRS-034 T3": ("passed", "")}
    assert report["release"] is None and report["dependencies"] == []
    assert any("no release record" in e for e in report["errors"])
    assert any("cannot be checked" in e for e in report["errors"])
    assert (out / "validation-report.html").is_file() and report["path"] == str(out / "validation-report.html")
    assert "INCOMPLETE build validation: 1 of 1 test point(s) passed" in result.stderr


@pytest.mark.dhf_links("SRS-071")
@pytest.mark.dhf_testing("T1")
def test_a_failing_case_fails_the_validation_and_names_the_point(tmp_path, monkeypatch) -> None:
    result, report, _ = _run(tmp_path, monkeypatch, [
        Case("ok", "SRS-007", ("T4",), _nothing, _passes, tools=()),
        Case("bad", "SRS-009", ("T2",), _nothing, _fails, tools=()),
    ])
    assert result.exit_code == 1
    assert report["result"] == "failed"
    assert _points(report)["SRS-009 T2"] == ("failed", "bad: the gate let the omission through")
    assert _points(report)["SRS-007 T4"] == ("passed", "")
    assert "FAIL [validation] FAILED SRS-009 T2" in result.stderr


@pytest.mark.dhf_links("SRS-071")
@pytest.mark.dhf_testing("T2")
def test_a_case_that_crashes_is_a_failure_not_a_traceback(tmp_path, monkeypatch) -> None:
    result, report, _ = _run(tmp_path, monkeypatch, [Case("boom", "SRS-007", ("T4",), _nothing, _crashes, tools=())])
    assert result.exit_code == 1 and "Traceback" not in result.stderr
    assert _points(report)["SRS-007 T4"] == ("failed", "boom: KeyError: 'errors'")


@pytest.mark.dhf_links("SRS-071")
@pytest.mark.dhf_testing("T3")
def test_a_project_that_cannot_be_built_fails_every_case_on_it(tmp_path, monkeypatch) -> None:
    def broken(root: Path) -> None:
        raise OSError("disk full")

    _, report, _ = _run(tmp_path, monkeypatch, [Case("one", "SRS-007", ("T4",), broken, _passes, tools=()),
                                                Case("two", "SRS-009", ("T2",), broken, _passes, tools=())])
    assert report["result"] == "failed"
    assert all(status == "failed" and "could not be built" in message for status, message in _points(report).values())


@pytest.mark.dhf_links("SRS-072")
@pytest.mark.dhf_testing("T1")
def test_a_missing_tool_leaves_its_points_not_run_and_the_result_incomplete(tmp_path, monkeypatch) -> None:
    result, report, _ = _run(tmp_path, monkeypatch, [
        Case("signs", "SRS-016", ("T1", "T2"), _nothing, _passes, tools=("no-such-tool-for-medharness",)),
    ])
    assert result.exit_code == 1
    assert report["result"] == "incomplete"
    assert _points(report) == {f"SRS-016 {p}": ("not_run", "signs: no-such-tool-for-medharness not found on PATH")
                               for p in ("T1", "T2")}
    assert "2 of 2 test point(s) were not run" in report["errors"]


def _record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tested_with: list[dict] = ()) -> None:
    record = tmp_path / "release.json"
    record.write_text(json.dumps({
        "version": "9.9.9", "commit": "abc", "evidence": ["medharness-9.9.9-junit.xml"], "tested_with": list(tested_with),
        "requirements": [{"id": "SRS-007", "title": "verify impact names a dependent", "risk": "high",
                          "points": [{"id": "T1", "text": "a | b"}, {"id": "T4", "text": "seeded"}]}],
    }), encoding="utf-8")
    monkeypatch.setattr(validation, "RELEASE_RECORD", record)


@pytest.mark.dhf_links("SRS-072")
@pytest.mark.dhf_testing("T3")
def test_a_point_of_the_release_record_no_case_exercises_is_not_run(tmp_path, monkeypatch) -> None:
    _record(tmp_path, monkeypatch)
    result, report, _ = _run(tmp_path, monkeypatch, [Case("seeded", "SRS-007", ("T4",), _nothing, _passes, tools=())])
    assert result.exit_code == 1 and report["result"] == "incomplete"
    assert _points(report) == {"SRS-007 T1": ("not_run", "no validation case exercises this point yet"),
                               "SRS-007 T4": ("passed", "")}
    assert "1 of 2 test point(s) were not run" in report["errors"]


@pytest.mark.dhf_links("SRS-073")
@pytest.mark.dhf_testing("T2", "T4")
def test_dependency_deviations_are_listed_and_the_report_carries_the_requirement_text(tmp_path, monkeypatch) -> None:
    _record(tmp_path, monkeypatch, [{"name": "click", "version": "0.0.1", "marker": None},
                                    {"name": "no-such-dependency", "version": "1.0", "marker": "sys_platform == 'win32'"}])
    _, report, out = _run(tmp_path, monkeypatch, [Case("seeded", "SRS-007", ("T1", "T4"), _nothing, _passes, tools=())])
    assert report["release"] == {"version": "9.9.9", "commit": "abc", "evidence": ["medharness-9.9.9-junit.xml"]}
    assert {d["name"]: d["status"] for d in report["dependencies"]} == {"click": "different", "no-such-dependency": "missing"}
    assert report["result"] == "incomplete" and not any("click" in e or "dependency" in e for e in report["errors"])
    html = (out / "validation-report.html").read_text(encoding="utf-8")
    assert "verify impact names a dependent" in html and "a | b" in html and "a \\| b" not in html


@pytest.mark.dhf_links("SRS-071")
@pytest.mark.dhf_testing("T4")
def test_a_case_for_a_point_the_release_does_not_define_fails(tmp_path, monkeypatch) -> None:
    record = tmp_path / "release.json"
    record.write_text(json.dumps({"version": "9.9.9", "commit": "abc", "evidence": [], "tested_with": [],
                                  "requirements": [{"id": "SRS-007", "title": "t", "risk": "high",
                                                    "points": [{"id": "T1", "text": "x"}]}]}), encoding="utf-8")
    monkeypatch.setattr(validation, "RELEASE_RECORD", record)
    _, report, _ = _run(tmp_path, monkeypatch, [Case("stray", "SRS-007", ("T9",), _nothing, _passes, tools=())])
    assert report["result"] == "failed"
    assert "case stray exercises SRS-007 T9, which the release does not define" in report["errors"]


@pytest.mark.dhf_links("SRS-073")
@pytest.mark.dhf_testing("T3")
def test_it_never_reads_the_dhf_it_is_given(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(validation, "CASES", [Case("a", "SRS-034", ("T3",), _nothing, _passes, tools=())])
    result = CliRunner().invoke(main, ["--dhf", str(tmp_path / "no-such-dhf"), "build", "validation",
                                       "--out-dir", str(tmp_path / "out")])
    assert json.loads(result.stdout)["requirements"][0]["points"][0]["status"] == "passed"
    assert not (tmp_path / "no-such-dhf").exists()
