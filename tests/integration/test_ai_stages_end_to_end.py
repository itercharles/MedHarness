"""`build plan` and `build code` from the command line to the files they leave.

A scripted stand-in for the `claude` CLI (tests/fixtures/fake_claude.py) plays the
model, so the whole orchestration runs for real: prompt assembly, the model
subprocess, deterministic validation, the fix and review loops, what is left
uncommitted, and what the answer says. What this cannot test is the model's own
judgement; that is what a run against a real repository is for.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from medharness.cli import main
from medharness.results import CodeReport, PlanReport
from medharness.workflows.init import _replace_placeholders, _scaffold_dhf

FAKE = Path(__file__).resolve().parents[1] / "fixtures" / "fake_claude.py"
MH = f"{shlex.quote(sys.executable)} -m medharness --dhf DHF"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed project with an `origin/main`, a fake `claude` first on PATH."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, capture_output=True)
    _git(work, "config", "user.email", "ci@example.com")
    _git(work, "config", "user.name", "ci")
    _scaffold_dhf(work)
    _replace_placeholders(work, "Ai")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "base")
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "fetch", "-q", "origin")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text(f"#!{sys.executable}\nimport runpy\nrunpy.run_path({str(FAKE)!r}, run_name='__main__')\n")
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(tmp_path / "calls.jsonl"))
    monkeypatch.setenv("FAKE_CLAUDE_PLAN", str(tmp_path / "plan.json"))
    monkeypatch.chdir(work)
    for name in ("MEDHARNESS_DESIGN_MODEL", "MEDHARNESS_DESIGN_REVIEW_MODEL", "MEDHARNESS_DEVELOP_MODEL",
                 "MEDHARNESS_CODE_REVIEW_MODEL", "ANTHROPIC_MODEL"):
        monkeypatch.delenv(name, raising=False)
    return work


def _plan(tmp: Path, **stages) -> None:
    (tmp / "plan.json").write_text(json.dumps(stages))


def _calls(project: Path) -> list[dict]:
    log = project.parent / "calls.jsonl"
    lines = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return [c for c in lines if not c["stage"].endswith(":ran")]


def _json(data: dict) -> str:
    return shlex.quote(json.dumps(data))


def _impact(created=(), unchanged=(), anchors=()) -> dict:
    """A complete `impact_analysis`, as `build plan` leaves it."""
    return {
        "assumptions": ["the issue means what it says"],
        "anchors": [{"id": uid, "evidence": "named in the issue"} for uid in anchors],
        "unchanged": [{"id": uid, "reason": "still holds"} for uid in unchanged],
        "created": [{"id": uid, "reason": "nothing covers it"} for uid in created],
        "dimensions": [{"dimension": d, "verdict": "not_required", "reason": "no effect", "items": []}
                       for d in ("product", "requirements", "architecture", "risk", "soup",
                                 "test", "regulatory", "security", "usability")],
    }


DESIGN = [
    f"{MH} item create --type CRS --data " + _json({
        "title": "Export PDF", "content": "The user can export a report as PDF.",
        "derives_from": ["UC-001"], "verification_criteria": "A PDF is produced"}),
    f"{MH} item create --type SYS --data " + _json({
        "title": "PDF export", "content": "The system exports PDF.", "category": "Functional",
        "satisfies": ["CRS-002"], "verification_method": ["Test"], "verification_criteria": "PDF opens"}),
    f"{MH} item create --type SYSARCH --data " + _json({
        "title": "PDF service", "content": "A service renders reports.", "design": ["SYS-002"]}),
    f"{MH} item create --type SRS --data " + _json({
        "title": "PDF writer", "content": "The software writes PDF.", "derives_from": ["SYS-002"],
        "verification_method": ["Test"], "verification_criteria": "file is valid",
        "testing": "T1: the output opens"}),
    f"{MH} item create --type SWDD --data " + _json({
        "title": "PDF writer design", "content": "Uses a PDF library.", "implements": ["SRS-002"],
        "module": ["MODULE-001"]}),
    f"{MH} item update CR-001 --data " + _json({
        "triage_result": {"verdict": "approved"}, "affected_risk_items": [],
        "reviewed_items": ["UC-001", "MODULE-001"],
        "impact_analysis": _impact(
            created=("CRS-002", "SYS-002", "SYSARCH-002", "SRS-002", "SWDD-002"),
            unchanged=("UC-001", "MODULE-001"), anchors=("UC-001",)),
        "implementation_notes": "Add a PDF writer."}),
]
APPROVED_REVIEW = (
    "mkdir -p docs/reviews && printf '# Design Review\\n\\n**Verdict:** Approved\\n' > docs/reviews/CR-001-Design-Review.md"
)


def _run(*args: str):
    result = CliRunner().invoke(main, ["--dhf", "DHF", *args])
    assert "Traceback" not in (result.stderr or "") + result.output, result.stderr
    return result


def _report(result) -> dict:
    """The run report, which must match what interface.md declares for the command."""
    report = json.loads(result.stdout.splitlines()[0])
    (PlanReport if report["stage"] == "generate_dhf" else CodeReport).model_validate(report)
    return report


class TestBuildPlan:
    def test_a_compliant_run_leaves_the_design_uncommitted_and_the_cr_recording_it(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])
        head = _git(project, "rev-parse", "HEAD")

        result = _run("build", "plan", "--cr", "CR-001")

        report = _report(result)
        assert result.exit_code == 0, result.stderr
        assert report["outcome"] == "ok" and report["errors"] == []
        assert _git(project, "rev-parse", "HEAD") == head, "the run committed"
        assert _git(project, "status", "--porcelain"), "the work is in the working tree"
        cr = json.loads(_run("item", "get", "CR-001").stdout)
        assert cr["affected_items"] and all(not i.startswith("CR-") for i in cr["affected_items"])
        assert [c["stage"] for c in _calls(project)] == ["design", "design_review"]

    def test_a_repository_whose_base_branch_is_not_main_names_it_with_since_ref(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _git(project, "push", "-q", "origin", "HEAD:trunk")
        _git(project, "fetch", "-q", "origin")
        _git(project, "update-ref", "-d", "refs/remotes/origin/main")
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": DESIGN}, {"run": []}],
              design_review=[{"run": [APPROVED_REVIEW]}])

        by_default = _report(_run("build", "plan", "--cr", "CR-001"))
        assert any(e["field"] == "changed_items" and "origin/main" in e["issue"] for e in by_default["errors"])

        _git(project, "checkout", "-q", "--", ".")
        _git(project, "clean", "-fdq", "--", "DHF", "docs")
        result = _run("build", "plan", "--cr", "CR-001", "--since-ref", "origin/trunk")
        report = _report(result)
        assert result.exit_code == 0, result.stderr
        assert report["inputs"]["since_ref"] == "origin/trunk" and report["errors"] == []

    def test_the_branch_origin_points_at_is_the_base_without_any_option(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _git(project, "push", "-q", "origin", "HEAD:trunk")
        _git(project, "fetch", "-q", "origin")
        _git(project, "update-ref", "-d", "refs/remotes/origin/main")
        _git(project, "remote", "set-head", "origin", "trunk")
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001")

        assert result.exit_code == 0, result.stderr
        assert _report(result)["inputs"]["since_ref"] == "origin/trunk"
        changes = _run("verify", "changes", "--cr", "CR-001")
        assert "since origin/trunk" in json.loads(changes.stdout.splitlines()[0])["summary"]

    def test_a_design_that_leaves_out_an_item_it_records_is_fixed_in_a_second_pass(
        self, project: Path, tmp_path: Path,
    ) -> None:
        broken = DESIGN[:4] + DESIGN[5:]
        _plan(tmp_path, design=[{"run": broken}, {"run": [DESIGN[4]]}],
              design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001")

        assert result.exit_code == 0, result.stderr
        assert _report(result)["outcome"] == "corrected"
        design_calls = [c for c in _calls(project) if c["stage"] == "design"]
        assert len(design_calls) == 2
        assert "--resume" in design_calls[1]["flags"], "the fix pass must resume the model's session"

    def test_a_design_that_stays_broken_is_reported_and_exits_1(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _plan(tmp_path, design=[{"run": DESIGN[:4] + DESIGN[5:]}, {"run": []}],
              design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001")

        report = _report(result)
        assert result.exit_code == 1 and report["outcome"] == "completed_with_errors"
        assert any("SWDD-002" in e["issue"] for e in report["errors"]), report["errors"]

    def test_a_model_that_fails_is_a_tool_error(self, project: Path, tmp_path: Path) -> None:
        _plan(tmp_path, design=[{"exit": 1, "say": "rate limited"}])
        result = _run("build", "plan", "--cr", "CR-001")
        assert result.exit_code == 1 and _report(result)["outcome"] == "tool_error"

    def test_a_missing_claude_cli_says_so(self, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import shutil

        monkeypatch.setenv("PATH", str(Path(shutil.which("git")).parent))
        monkeypatch.setattr(shutil, "which", lambda *_: None) if False else None
        (project.parent / "bin" / "claude").unlink()
        result = _run("build", "plan", "--cr", "CR-001")
        assert result.exit_code == 1
        assert "claude CLI not found" in result.stdout + result.stderr

    def test_commits_the_agent_made_are_undone_and_its_work_kept(
        self, project: Path, tmp_path: Path,
    ) -> None:
        commit = "git add -A && git commit -qm 'agent commit'"
        _plan(tmp_path, design=[{"run": DESIGN + [commit]}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])
        head = _git(project, "rev-parse", "HEAD")

        result = _run("build", "plan", "--cr", "CR-001")

        assert _git(project, "rev-parse", "HEAD") == head
        assert _git(project, "status", "--porcelain")
        assert any(w["code"] == "agent_commits_undone" for w in _report(result)["warnings"])




def _design_merged(project: Path) -> None:
    """The design PR has been merged: the items and the CR's notes are on `origin/main`."""
    for command in DESIGN:
        subprocess.run(command, shell=True, check=True, capture_output=True, cwd=project)
    _git(project, "add", "-A")
    _git(project, "commit", "-qm", "design")
    _git(project, "push", "-q", "origin", "HEAD:main")
    _git(project, "fetch", "-q", "origin")


def _write(path: str, text: str) -> str:
    """A shell command that writes `text` to `path`, for the fake model to run."""
    code = f"import pathlib; p = pathlib.Path({path!r}); p.parent.mkdir(parents=True, exist_ok=True); p.write_text({text!r})"
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


CODE = [_write("src/pdf.py", "def write():\n    return b'%PDF'\n"),
        _write("tests/test_pdf.py", "def test_write():\n    assert True\n")]


class TestBuildPlanChangeImpact:
    UPDATE = [
        f"{MH} item update SYS-001 --data " + _json({"content": "Changed.", "verification_criteria": "PDF opens"}),
        f"{MH} item update CR-001 --data " + _json({
            "triage_result": {"verdict": "approved"}, "implementation_notes": "Change SYS-001.",
            "affected_risk_items": ["RCM-001", "RISK-001"], "reviewed_items": ["CRS-001"],
            "impact_analysis": _impact(unchanged=("CRS-001",), anchors=("SYS-001",))}),
    ]
    DEPENDENTS = ["SRS-001", "SYSARCH-001", "RCM-001"]
    REVIEW = f"{MH} item update CR-001 --data " + _json({
        "reviewed_items": ["CRS-001", *DEPENDENTS],
        "impact_analysis": _impact(unchanged=("CRS-001", *DEPENDENTS), anchors=("SYS-001",))})

    def test_a_dependent_the_model_left_alone_is_fixed_in_the_second_pass(self, project: Path, tmp_path: Path) -> None:
        _plan(tmp_path, design=[{"run": self.UPDATE}, {"run": [self.REVIEW]}],
              design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001")

        report = _report(result)
        assert result.exit_code == 0, result.stderr
        assert report["outcome"] == "corrected"
        fix_pass = [c for c in _calls(project) if c["stage"] == "design"][1]
        assert "SRS-001 depends on SYS-001" in fix_pass["prompt"]

    def test_a_dependent_that_stays_unreviewed_is_reported(self, project: Path, tmp_path: Path) -> None:
        _plan(tmp_path, design=[{"run": self.UPDATE}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])
        result = _run("build", "plan", "--cr", "CR-001")
        report = _report(result)
        assert result.exit_code == 1 and report["outcome"] == "completed_with_errors"
        assert {e["field"] for e in report["errors"]} == {"impact.RCM-001", "impact.SRS-001", "impact.SYSARCH-001"}


class TestBuildPlanImpactAnalysis:
    """The record of what was looked at and left alone is checked inside `build plan`."""

    CREATED = ("CRS-002", "SYS-002", "SYSARCH-002", "SRS-002", "SWDD-002")

    def _plan_and_run(self, tmp_path: Path, commands: list[str]) -> dict:
        _plan(tmp_path, design=[{"run": commands}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])
        return _report(_run("build", "plan", "--cr", "CR-001"))

    def _cr(self, **fields) -> str:
        base = {"triage_result": {"verdict": "approved"}, "affected_risk_items": [],
                "implementation_notes": "Plan."}
        return f"{MH} item update CR-001 --data " + _json({**base, **fields})

    def _fields(self, report: dict) -> set[str]:
        return {e["field"] for e in report["errors"]}

    def test_a_complete_record_adds_no_error(self, project: Path, tmp_path: Path) -> None:
        report = self._plan_and_run(tmp_path, DESIGN)
        assert not [f for f in self._fields(report) if f.startswith("impact_analysis")]

    def test_a_run_that_wrote_no_record_is_told_which_field(self, project: Path, tmp_path: Path) -> None:
        report = self._plan_and_run(tmp_path, DESIGN[:-1] + [self._cr()])
        assert "impact_analysis" in self._fields(report)
        fix = next(e["fix"] for e in report["errors"] if e["field"] == "impact_analysis")
        assert "item update CR-001" in fix

    def test_a_created_item_without_a_reason_is_an_error(self, project: Path, tmp_path: Path) -> None:
        record = _impact(created=self.CREATED[:-1], unchanged=("UC-001", "MODULE-001"), anchors=("UC-001",))
        report = self._plan_and_run(tmp_path, DESIGN[:-1] + [
            self._cr(reviewed_items=["UC-001", "MODULE-001"], impact_analysis=record)])
        errors = [e for e in report["errors"] if e["field"] == "impact_analysis.created"]
        assert [e["issue"].split()[1] for e in errors] == ["SWDD-002"]

    def test_a_parent_that_is_neither_changed_nor_reviewed_is_an_error(self, project: Path, tmp_path: Path) -> None:
        report = self._plan_and_run(tmp_path, DESIGN[:-1] + [self._cr(
            reviewed_items=[], impact_analysis=_impact(created=self.CREATED))])
        parents = [e["issue"] for e in report["errors"] if e["field"] == "impact_analysis.parents"]
        assert any("CRS-002 changed but its parent UC-001" in issue for issue in parents)

    def test_the_parents_of_a_design_item_need_not_be_reviewed(self, project: Path, tmp_path: Path) -> None:
        report = self._plan_and_run(tmp_path, DESIGN[:-1] + [self._cr(
            reviewed_items=["UC-001"], impact_analysis=_impact(created=self.CREATED, unchanged=("UC-001",)))])
        assert "impact_analysis.parents" not in self._fields(report)

    def test_a_risk_control_of_a_changed_item_must_be_recorded(self, project: Path, tmp_path: Path) -> None:
        update = f"{MH} item update SYS-001 --data " + _json({"content": "Changed.", "verification_criteria": "PDF opens"})
        reviewed = ["CRS-001", "SRS-001", "SYSARCH-001", "RCM-001"]
        report = self._plan_and_run(tmp_path, [update, self._cr(
            reviewed_items=reviewed, impact_analysis=_impact(unchanged=reviewed, anchors=("SYS-001",)))])
        risk = [e for e in report["errors"] if e["field"] == "impact_analysis.risk"]
        assert {e["issue"].split(" ")[1] for e in risk} == {"RCM-001", "RISK-001"}
        assert any("RCM-001 controls SYS-001" in e["issue"] for e in risk)
        assert any("RISK-001" in e["fix"] and "affected_risk_items" in e["fix"] for e in risk)
        assert not [f for f in self._fields(report) if f.startswith("impact.")]

    def test_a_created_item_that_reads_like_an_existing_one_is_a_warning(self, project: Path, tmp_path: Path) -> None:
        sys_001 = json.loads(_run("item", "get", "SYS-001").stdout)
        copy = {k: sys_001[k] for k in ("title", "content", "category", "satisfies", "verification_method",
                                        "verification_criteria") if k in sys_001}
        create = f"{MH} item create --type SYS --data " + _json(copy)
        report = self._plan_and_run(tmp_path, [create, self._cr()])
        duplicate = [w for w in report["warnings"] if w["code"] == "possible_duplicate"]
        assert len(duplicate) == 1
        assert "SYS-002 reads like SYS-001" in duplicate[0]["message"]
        assert "possible_duplicate" not in {e["field"] for e in report["errors"]}, "a warning, not an error"

    def _edit_swdd(self, tmp_path: Path, content: str) -> list[dict]:
        update = f"{MH} item update SWDD-001 --data " + _json({"content": content})
        report = self._plan_and_run(tmp_path, [update, self._cr()])
        return [w for w in report["warnings"] if w["code"] == "large_edit"]

    def test_an_existing_item_that_gains_many_lines_is_a_warning(self, project: Path, tmp_path: Path) -> None:
        warnings = self._edit_swdd(tmp_path, "\n".join(f"Step {n} of a second behaviour." for n in range(60)))
        assert [w["message"].split()[0] for w in warnings] == ["SWDD-001"]

    def test_a_one_line_change_to_an_existing_item_is_not(self, project: Path, tmp_path: Path) -> None:
        assert self._edit_swdd(tmp_path, "One changed line.") == []

    def _copy_of(self, uid: str, item_type: str, **extra) -> str:
        item = json.loads(_run("item", "get", uid).stdout)
        copy = {k: item[k] for k in ("title", "content", "category", "satisfies", "verification_method",
                                     "verification_criteria", "description") if k in item}
        return f"{MH} item create --type {item_type} --data " + _json({**copy, **extra})

    def _duplicates(self, tmp_path: Path, commands: list[str]) -> list[dict]:
        report = self._plan_and_run(tmp_path, commands + [self._cr()])
        return [w for w in report["warnings"] if w["code"] == "possible_duplicate"]

    def test_a_cr_that_reads_like_another_cr_is_not_a_possible_duplicate(self, project: Path, tmp_path: Path) -> None:
        assert self._duplicates(tmp_path, [self._copy_of("CR-001", "CR")]) == []

    def test_an_item_that_reads_like_a_cancelled_one_is_not_a_possible_duplicate(self, project: Path, tmp_path: Path) -> None:
        cancel = f"{MH} item update SYS-001 --data " + _json({"status": "cancelled"})
        assert self._duplicates(tmp_path, [cancel, self._copy_of("SYS-001", "SYS")]) == []

    def _points(self, tmp_path: Path, **fields) -> list[dict]:
        update = f"{MH} item update SRS-001 --data " + _json(fields)
        report = self._plan_and_run(tmp_path, [update, self._cr()])
        return [w for w in report["warnings"] if w["code"] == "test_points_unchanged"]

    def test_a_requirement_that_says_more_without_new_test_points_is_a_warning(self, project: Path, tmp_path: Path) -> None:
        warnings = self._points(tmp_path, content="The export also writes a checksum.")
        assert [w["message"].split()[0] for w in warnings] == ["SRS-001"]

    def test_a_requirement_whose_test_points_changed_with_it_is_not(self, project: Path, tmp_path: Path) -> None:
        assert self._points(tmp_path, content="The export also writes a checksum.",
                            testing="T1: export opens\nT2: the checksum matches") == []

    def test_a_change_that_leaves_the_requirement_unsaid_is_not(self, project: Path, tmp_path: Path) -> None:
        assert self._points(tmp_path, status="draft") == []

    def test_a_rejected_cr_needs_no_record(self, project: Path, tmp_path: Path) -> None:
        reject = f"{MH} item update CR-001 --data " + _json(
            {"status": "rejected", "impact_assessment": "duplicate of CR-002"})
        report = self._plan_and_run(tmp_path, [reject])
        assert not [f for f in self._fields(report) if f.startswith("impact_analysis")]


class TestBuildCode:
    def test_a_compliant_run_leaves_the_code_uncommitted_and_lists_it(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _design_merged(project)
        _plan(tmp_path, develop=[{"run": CODE}], code_review=[{"say": "**Verdict:** Approved"}])
        head = _git(project, "rev-parse", "HEAD")

        result = _run("build", "code", "--cr", "CR-001")

        report = _report(result)
        assert result.exit_code == 0, result.stderr
        assert report["outcome"] == "ok"
        assert {"src/pdf.py", "tests/test_pdf.py"} <= set(report["artifacts"]["files_changed"]["created"])
        assert _git(project, "rev-parse", "HEAD") == head and _git(project, "status", "--porcelain")
        assert [c["stage"] for c in _calls(project)] == ["develop", "code_review"]

    def test_the_code_paths_can_be_narrowed(
        self, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _design_merged(project)
        monkeypatch.setenv("MEDHARNESS_CODE_PATHS", "lib/")
        _plan(tmp_path, develop=[{"run": CODE + [_write("lib/pdf.py", "x = 1\n")]}],
              code_review=[{"say": "**Verdict:** Approved"}])

        report = _report(_run("build", "code", "--cr", "CR-001"))

        assert report["artifacts"]["files_changed"]["created"] == ["lib/pdf.py"]

    def test_a_review_that_asks_for_changes_sends_the_model_back_until_it_approves(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _design_merged(project)
        _plan(tmp_path, develop=[{"run": CODE}],
              code_review=[{"say": "**Verdict:** Needs Revision\n- [ ] no test for an empty report"},
                           {"say": "**Verdict:** Approved"}],
              code_fix=[{"run": ["echo '# empty report handled' >> src/pdf.py"]}])

        result = _run("build", "code", "--cr", "CR-001")

        assert result.exit_code == 0, result.stderr
        assert [c["stage"] for c in _calls(project)] == ["develop", "code_review", "code_fix", "code_review"]
        assert "empty report handled" in (project / "src" / "pdf.py").read_text()

    def test_a_review_that_never_approves_stops_after_three_rounds(
        self, project: Path, tmp_path: Path,
    ) -> None:
        _design_merged(project)
        _plan(tmp_path, develop=[{"run": CODE}],
              code_review=[{"say": "**Verdict:** Needs Revision\n- [ ] still wrong"}], code_fix=[{"run": []}])

        result = _run("build", "code", "--cr", "CR-001")

        stages = [c["stage"] for c in _calls(project)]
        assert stages.count("code_review") == 3 and stages.count("code_fix") == 2, stages
        assert _report(result)["diagnostics"]["code_review_verdict"] == "needs_revision"

    def test_a_model_that_fails_is_a_tool_error(self, project: Path, tmp_path: Path) -> None:
        _design_merged(project)
        _plan(tmp_path, develop=[{"exit": 1, "say": "overloaded"}])
        result = _run("build", "code", "--cr", "CR-001")
        assert result.exit_code == 1 and _report(result)["outcome"] == "tool_error"


@pytest.fixture
def pr(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """PR 7 on branch design/CR-001 — with a fake `gh` answering for it."""
    gh = tmp_path / "bin" / "gh"
    gh.write_text(f"#!{sys.executable}\nimport runpy\nrunpy.run_path({str(FAKE.with_name('fake_gh.py'))!r}, run_name='__main__')\n")
    gh.chmod(0o755)
    _git(project, "checkout", "-q", "-b", "design/CR-001")
    _git(project, "push", "-q", "origin", "design/CR-001")
    monkeypatch.setenv("FAKE_GH_STATE", str(tmp_path / "gh.json"))

    def state(**fields) -> None:
        head = _git(project, "rev-parse", "HEAD")
        (tmp_path / "gh.json").write_text(json.dumps({"head_sha": head, "branch": "design/CR-001", **fields}))

    state()
    return state


def _remote_files(project: Path, branch: str) -> list[str]:
    remote = project.parent / "remote.git"
    return subprocess.run(["git", "-C", str(remote), "ls-tree", "-r", "--name-only", branch],
                          capture_output=True, text=True, check=True).stdout.split()


class TestBuildCodeChecks:
    """`--check` is run by the harness, so the model cannot skip it or report a guess."""

    APPROVED = [{"say": "**Verdict:** Approved"}]

    def _code(self, project: Path, tmp_path: Path, *extra: str, **stages) -> object:
        _design_merged(project)
        _plan(tmp_path, develop=[{"run": CODE}], code_review=self.APPROVED, **stages)
        return _run("build", "code", "--cr", "CR-001", *extra)

    def test_the_model_is_told_which_commands_the_harness_will_run(self, project: Path, tmp_path: Path) -> None:
        self._code(project, tmp_path, "--check", "true")
        develop = next(c for c in _calls(project) if c["stage"] == "develop")
        assert "## Checks That Must Pass" in develop["prompt"] and "- `true`" in develop["prompt"]

    def test_a_passing_check_is_in_the_report(self, project: Path, tmp_path: Path) -> None:
        result = self._code(project, tmp_path, "--check", "true")
        assert result.exit_code == 0, result.stderr
        assert _report(result)["checks"] == [{"command": "true", "exit_code": 0, "passed": True}]
        assert "check_fix" not in [c["stage"] for c in _calls(project)]

    def test_a_run_without_check_reports_none(self, project: Path, tmp_path: Path) -> None:
        assert "checks" not in _report(self._code(project, tmp_path))
        develop = next(c for c in _calls(project) if c["stage"] == "develop")
        assert "Checks That Must Pass" not in develop["prompt"]

    def test_a_failure_goes_back_to_the_model_and_the_run_passes_once_it_is_fixed(
        self, project: Path, tmp_path: Path,
    ) -> None:
        result = self._code(project, tmp_path, "--check", "test -f src/fixed.txt",
                            check_fix=[{"run": ["touch src/fixed.txt"]}])
        assert result.exit_code == 0, result.stderr
        assert [c["stage"] for c in _calls(project)] == ["develop", "code_review", "check_fix"]
        fix = next(c for c in _calls(project) if c["stage"] == "check_fix")
        assert "`test -f src/fixed.txt` exited 1" in fix["prompt"]
        assert _report(result)["checks"][0]["passed"] is True

    def test_a_check_that_never_passes_fails_the_run_after_two_fix_attempts(
        self, project: Path, tmp_path: Path,
    ) -> None:
        result = self._code(project, tmp_path, "--check", "echo broken >&2; exit 3", check_fix=[{"run": []}])
        report = _report(result)
        assert result.exit_code == 1
        assert [c["stage"] for c in _calls(project)].count("check_fix") == 2
        assert report["checks"] == [{"command": "echo broken >&2; exit 3", "exit_code": 3, "passed": False}]
        error = next(e for e in report["errors"] if e["field"] == "check")
        assert "exited 3" in error["issue"] and "broken" in error["issue"]

    def test_a_command_that_cannot_run_is_a_failure_not_a_guess(self, project: Path, tmp_path: Path) -> None:
        result = self._code(project, tmp_path, "--check", "no-such-tool-for-this-test", check_fix=[{"run": []}])
        assert result.exit_code == 1
        assert _report(result)["checks"][0]["exit_code"] == 127

    def test_every_check_must_pass(self, project: Path, tmp_path: Path) -> None:
        result = self._code(project, tmp_path, "--check", "true", "--check", "false", check_fix=[{"run": []}])
        assert result.exit_code == 1
        assert [c["passed"] for c in _report(result)["checks"]] == [True, False]

    def test_the_prompt_for_an_agent_already_running_lists_them_too(self, project: Path, tmp_path: Path) -> None:
        _design_merged(project)
        result = _run("build", "code", "--cr", "CR-001", "--check", "pnpm test", "--prompt")
        assert "- `pnpm test`" in result.stdout

    def test_a_pull_request_gets_nothing_pushed_while_a_check_fails(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        before = _remote_files(project, "design/CR-001")
        result = self._code(project, tmp_path, "--check", "false", "--pr", "7", check_fix=[{"run": []}])
        assert result.exit_code == 1
        assert not any(e["field"] == "pr_push" for e in _report(result)["errors"])
        assert _remote_files(project, "design/CR-001") == before


class TestWithAPullRequest:
    def test_the_work_is_committed_and_pushed_to_the_prs_branch(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001", "--pr", "7")

        assert result.exit_code == 0, result.stderr
        assert _git(project, "status", "--porcelain") == ""
        assert any(f.endswith("SRS-002.yaml") for f in _remote_files(project, "design/CR-001"))

    def test_the_prs_base_branch_is_what_the_run_compares_against(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        _git(project, "push", "-q", "origin", "HEAD:release")
        _git(project, "fetch", "-q", "origin")
        pr(base="release")
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001", "--pr", "7")

        assert _report(result)["inputs"]["since_ref"] == "origin/release"

    def test_a_reviewer_asking_for_changes_reaches_the_model(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        head = _git(project, "rev-parse", "HEAD")
        pr(reviews=[{"state": "CHANGES_REQUESTED", "commit_id": head, "body": "Please assess the battery risk",
                     "user": {"login": "reviewer"}}])
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        _run("build", "plan", "--cr", "CR-001", "--pr", "7")

        first = next(c for c in _calls(project) if c["stage"] == "design")
        assert "Please assess the battery risk" in first["prompt"]

    def test_an_approval_asks_for_nothing_so_the_run_generates_afresh(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        head = _git(project, "rev-parse", "HEAD")
        pr(reviews=[{"state": "APPROVED", "commit_id": head, "body": "Looks good", "user": {"login": "reviewer"}}])
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        _run("build", "plan", "--cr", "CR-001", "--pr", "7")

        first = next(c for c in _calls(project) if c["stage"] == "design")
        assert "Looks good" not in first["prompt"]

    def test_a_push_that_fails_is_reported_not_swallowed(
        self, project: Path, tmp_path: Path, pr,
    ) -> None:
        _git(project, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
        _plan(tmp_path, design=[{"run": DESIGN}, {"run": []}], design_review=[{"run": [APPROVED_REVIEW]}])

        result = _run("build", "plan", "--cr", "CR-001", "--pr", "7")

        assert result.exit_code == 1
        assert any(e["field"] == "pr_push" for e in _report(result)["errors"])

