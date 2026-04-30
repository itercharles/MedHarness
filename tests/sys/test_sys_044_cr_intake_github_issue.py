"""
Tests for GitHub issue-to-CR intake workflow.

@links: SYS-041
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from compliantflow.cli import main
from compliantflow.cr_intake import (
    IssueContext,
    build_cr_data,
    current_iso_week_milestone,
    issue_has_cr_marker,
    next_cr_id,
    prepare_cr_from_issue,
)


class FakeIntakeAdapter:
    def __init__(self, items: list[dict[str, Any]] | None = None, created_id: str = "CR-034"):
        self.items = items or []
        self.created_id = created_id
        self.created_data: dict[str, Any] | None = None

    def list_items(self, doc_type: str | None = None) -> list[dict[str, Any]]:
        self.listed_doc_type = doc_type
        return self.items

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.items if item.get("id") == item_id), None)

    def create_item(self, data: dict[str, Any], author: str = "system", cr_id: str | None = None) -> dict[str, Any]:
        self.created_author = author
        self.created_data = data
        return {"id": self.created_id}


def make_issue(milestone: str = "2026-W18") -> IssueContext:
    return IssueContext(
        number=123,
        title="Add weekly CR intake",
        body=(
            "### Requested change\n\nCreate CR from accepted issue.\n\n"
            "### User value / justification\n\nWeekly intake is easier.\n\n"
            "### Acceptance criteria\n\n- CR PR is opened automatically.\n\n"
            "### Change category\n\nFeature"
        ),
        state="open",
        html_url="https://github.com/example/product/issues/123",
        author="charles",
        milestone=milestone,
    )


def write_issue_event(path: Path, issue: IssueContext) -> None:
    path.write_text(
        json.dumps({
            "issue": {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "html_url": issue.html_url,
                "user": {"login": issue.author},
                "milestone": {"title": issue.milestone},
            }
        }),
        encoding="utf-8",
    )


def test_TC_SYS_044_001_current_iso_week_milestone_uses_iso_year_and_week():
    """
    TC-SYS-044-001: ISO week milestone derives from ISO calendar year and week.

    @test_id: TC-SYS-044-001
    @links: SYS-041
    """
    assert current_iso_week_milestone(date(2026, 4, 26)) == "2026-W17"
    assert current_iso_week_milestone(date(2027, 1, 1)) == "2026-W53"


def test_TC_SYS_044_002_prepare_cr_creates_cr_with_adapter():
    """
    TC-SYS-044-002: issue intake creates a CR item through the DHF adapter.

    @test_id: TC-SYS-044-002
    @links: SYS-041
    """
    adapter = FakeIntakeAdapter()
    result = prepare_cr_from_issue(
        make_issue(),
        "2026-W18",
        [],
        write=True,
        adapter=adapter,
        marker_name="product-cr",
        branch_prefix="cr",
        title_prefix="cr",
    )

    assert result.should_create is True
    assert result.cr_id == "CR-034"
    assert result.branch == "cr/CR-034-from-issue-123-add-weekly-cr-intake"
    assert result.title == "cr(CR-034): Add weekly CR intake"
    assert adapter.created_author == "issue-to-cr"
    assert adapter.created_data == {
        "type": "CR",
        "title": "Add weekly CR intake",
        "description": "Create CR from accepted issue.\n\nSource issue: https://github.com/example/product/issues/123",
        "justification": "Weekly intake is easier.",
        "priority": "Medium",
        "requested_by": "charles",
        "target_version": "2026-W18",
        "category": "Feature",
        "content": "- CR PR is opened automatically.",
    }


def test_TC_SYS_044_003_prepare_cr_skips_wrong_milestone():
    """
    TC-SYS-044-003: issue intake skips issues outside the active milestone.

    @test_id: TC-SYS-044-003
    @links: SYS-041
    """
    result = prepare_cr_from_issue(
        make_issue("2026-W19"),
        "2026-W18",
        [],
        write=True,
        adapter=FakeIntakeAdapter(),
    )

    assert result.should_create is False
    assert "not active milestone" in result.reason


def test_TC_SYS_044_004_prepare_cr_skips_existing_marker_when_cr_in_dhf():
    """
    TC-SYS-044-004: issue intake skips an issue with an existing CR marker in DHF.

    @test_id: TC-SYS-044-004
    @links: SYS-041
    """
    comments = [{"body": "Already created\n<!-- product-cr: CR-034 -->"}]
    result = prepare_cr_from_issue(
        make_issue(),
        "2026-W18",
        comments,
        write=True,
        adapter=FakeIntakeAdapter([{"id": "CR-034", "description": ""}]),
        marker_name="product-cr",
    )

    assert result.should_create is False
    assert result.cr_id == "CR-034"


def test_TC_SYS_044_005_prepare_cr_retries_when_marker_cr_not_in_dhf():
    """
    TC-SYS-044-005: issue intake retries when marker exists but CR was never merged.

    @test_id: TC-SYS-044-005
    @links: SYS-041
    """
    comments = [{"body": "Previously attempted\n<!-- product-cr: CR-034 -->"}]
    adapter = FakeIntakeAdapter()
    result = prepare_cr_from_issue(
        make_issue(),
        "2026-W18",
        comments,
        write=True,
        adapter=adapter,
        marker_name="product-cr",
    )

    assert result.should_create is True
    assert result.cr_id == "CR-034"


def test_TC_SYS_044_006_prepare_cr_skips_existing_source_issue_url():
    """
    TC-SYS-044-006: issue intake skips when a DHF CR already references the issue URL.

    @test_id: TC-SYS-044-006
    @links: SYS-041
    """
    result = prepare_cr_from_issue(
        make_issue(),
        "2026-W18",
        [],
        write=True,
        adapter=FakeIntakeAdapter([
            {
                "id": "CR-034",
                "description": "Source issue: https://github.com/example/product/issues/123",
            }
        ]),
    )

    assert result.should_create is False
    assert result.cr_id == "CR-034"


def test_TC_SYS_044_007_dry_run_uses_next_cr_id_without_creating():
    """
    TC-SYS-044-007: dry-run intake computes the next CR ID without writing DHF items.

    @test_id: TC-SYS-044-007
    @links: SYS-041
    """
    adapter = FakeIntakeAdapter([{"id": "CR-001"}, {"id": "SYS-009"}, {"id": "CR-033"}])
    result = prepare_cr_from_issue(make_issue(), "2026-W18", [], write=False, adapter=adapter)

    assert result.should_create is True
    assert result.cr_id == "CR-034"
    assert adapter.created_data is None
    assert next_cr_id(adapter.items) == "CR-034"


def test_TC_SYS_044_008_marker_detection_uses_configured_marker_name():
    """
    TC-SYS-044-008: issue intake marker detection uses the configured marker name.

    @test_id: TC-SYS-044-008
    @links: SYS-041
    """
    assert issue_has_cr_marker([{"body": "<!-- product-cr: CR-099 -->"}], "product-cr") == "CR-099"
    assert issue_has_cr_marker([{"body": "<!-- webtps-cr: CR-099 -->"}], "product-cr") is None


def test_TC_SYS_044_009_build_cr_data_includes_issue_context():
    """
    TC-SYS-044-009: CR data maps issue form fields into DHF CR fields.

    @test_id: TC-SYS-044-009
    @links: SYS-041
    """
    data = build_cr_data(make_issue())
    assert data["type"] == "CR"
    assert data["title"] == "Add weekly CR intake"
    assert data["justification"] == "Weekly intake is easier."
    assert data["description"] == "Create CR from accepted issue.\n\nSource issue: https://github.com/example/product/issues/123"


def test_TC_SYS_044_010_cli_intake_github_issue_writes_output(monkeypatch, tmp_path):
    """
    TC-SYS-044-010: CLI intake command writes JSON output for workflow consumption.

    @test_id: TC-SYS-044-010
    @links: SYS-041
    """
    dhf_repo = tmp_path / "dhf-repo"
    (dhf_repo / "DHF").mkdir(parents=True)
    event_path = tmp_path / "event.json"
    comments_path = tmp_path / "comments.json"
    output_path = tmp_path / "intake.json"
    write_issue_event(event_path, make_issue())
    comments_path.write_text("[]\n", encoding="utf-8")
    adapter = FakeIntakeAdapter()

    monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root", lambda dhf_root: adapter)

    result = CliRunner().invoke(
        main,
        [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "intake-github-issue",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
            "--comments", str(comments_path),
            "--active-milestone", "2026-W18",
            "--marker-name", "product-cr",
            "--write",
            "--output", str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["should_create"] is True
    assert payload["cr_id"] == "CR-034"
    assert payload["branch"] == "cr/CR-034-from-issue-123-add-weekly-cr-intake"
    assert json.loads(result.output)["title"] == "cr(CR-034): Add weekly CR intake"


class TestIntakeGitHubIssueCI:
    """@links: SYS-044"""

    def _create_event(self, tmp_path, milestone="2026-W18"):
        import json as _json
        event_path = tmp_path / "event.json"
        event_path.write_text(_json.dumps({
            "action": "milestoned",
            "issue": {
                "number": 42,
                "title": "Test feature",
                "body": "### User value / justification\n\nTest justification.\n\n",
                "state": "open",
                "html_url": "https://github.com/acme/web/issues/42",
                "user": {"login": "dev"},
                "milestone": {"title": milestone},
            },
        }), encoding="utf-8")
        return event_path

    def _make_stub_adapter(self):
        class Stub:
            def create_item(self, data, **kwargs):
                return {"id": "CR-050", "type": "CR"}
            def get_item(self, uid):
                return {"id": uid, "status": "planned"}
            def list_items(self, doc_type=None):
                return []
            def get_available_transitions(self, uid):
                return []
        return Stub()

    def test_ci_intake_prepare_output(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        dhf_repo.mkdir()
        (dhf_repo / "DHF" / "config").mkdir(parents=True)
        (dhf_repo / "DHF" / "config" / "global.yaml").write_text("global_lifecycle: {}\n")
        (dhf_repo / "DHF" / "items" / "09_cr").mkdir(parents=True)
        event_path = self._create_event(tmp_path)
        comments_path = tmp_path / "comments.json"
        comments_path.write_text("[]\n", encoding="utf-8")
        output_path = tmp_path / "intake.json"
        github_output = tmp_path / "github-output.txt"

        monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root",
                            lambda dhf_root: self._make_stub_adapter())
        monkeypatch.setattr("compliantflow.cr_intake.current_iso_week_milestone",
                            lambda: "2026-W18")

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "intake-github-issue-ci",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
            "--comments", str(comments_path),
            "--marker-name", "test-cr",
            "--write",
            "--output", str(output_path),
            "--github-output", str(github_output),
        ])

        assert result.exit_code == 0, f"exit={result.exit_code} out={result.output!r} err={result.stderr!r}"
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload.get("should_create") is True
        assert payload.get("cr_id", "").startswith("CR-")
        assert "should_create=true" in github_output.read_text(encoding="utf-8")

    def test_ci_intake_admin_bypass_does_not_write(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        dhf_repo.mkdir()
        (dhf_repo / "DHF" / "config").mkdir(parents=True)
        (dhf_repo / "DHF" / "config" / "global.yaml").write_text("global_lifecycle: {}\n")
        event_path = self._create_event(tmp_path)
        comments_path = tmp_path / "comments.json"
        comments_path.write_text("[]\n", encoding="utf-8")

        monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root",
                            lambda dhf_root: self._make_stub_adapter())
        monkeypatch.setattr("compliantflow.cr_intake.current_iso_week_milestone",
                            lambda: "2026-W18")

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "intake-github-issue-ci",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
            "--comments", str(comments_path),
            "--marker-name", "test-cr",
            "--write",
        ])

        assert result.exit_code == 0, f"exit={result.exit_code} out={result.output!r}"
        payload = json.loads(result.output.strip())
        assert payload.get("should_create") is True
        assert payload.get("cr_id") == "CR-050"

    def test_ci_intake_no_write_only_computes_cr_id(self, monkeypatch, tmp_path):
        dhf_repo = tmp_path / "dhf"
        dhf_repo.mkdir()
        (dhf_repo / "DHF" / "config").mkdir(parents=True)
        (dhf_repo / "DHF" / "config" / "global.yaml").write_text("global_lifecycle: {}\n")
        (dhf_repo / "DHF" / "items" / "09_cr").mkdir(parents=True)
        event_path = self._create_event(tmp_path)
        comments_path = tmp_path / "comments.json"
        comments_path.write_text("[]\n", encoding="utf-8")

        monkeypatch.setattr("compliantflow.cli._make_adapter_for_dhf_root",
                            lambda dhf_root: self._make_stub_adapter())
        monkeypatch.setattr("compliantflow.cr_intake.current_iso_week_milestone",
                            lambda: "2026-W18")

        result = CliRunner().invoke(main, [
            "--dhf", str(dhf_repo / "DHF"),
            "cr", "workflow", "intake-github-issue-ci",
            "--dhf-repo", str(dhf_repo),
            "--event", str(event_path),
            "--comments", str(comments_path),
            "--marker-name", "test-cr",
        ])

        assert result.exit_code == 0, f"exit={result.exit_code} out={result.output!r}"
        payload = json.loads(result.output.strip())
        assert payload.get("should_create") is True
        files = list(dhf_repo.glob("DHF/items/09_cr/CR-*.yaml"))
        assert len(files) == 0, "no CR file should be written without --write"
