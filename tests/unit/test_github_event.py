"""Tests for medharness.services.github_event.

Parsing is a function of the payload dict and the event name, so these need no
event file, no environment and no git.
"""

from medharness.services.github_event import (
    GitHubEventContext,
    infer_stage,
    parse_github_event,
    plan_github_event,
)


def _no_git(sha: str) -> str:
    raise AssertionError(f"git consulted for {sha} when the branch named the CR")


def test_workflow_dispatch_with_manual_cr():
    result = parse_github_event({}, "workflow_dispatch", manual_cr_id="CR-001")

    assert result.cr_id == "CR-001"
    assert result.mode == "new"
    assert result.event_name == "workflow_dispatch"


def test_manual_cr_without_an_event_name_is_a_dispatch():
    result = parse_github_event({}, "", manual_cr_id="CR-001")

    assert result.event_name == "workflow_dispatch"
    assert result.mode == "new"


def test_manual_cr_overrides_any_event():
    result = parse_github_event(
        {"pull_request": {"head": {"ref": "feat/CR-002"}}}, "pull_request",
        manual_cr_id="CR-001",
    )

    assert result.cr_id == "CR-001"
    assert result.mode == "new"
    assert result.event_name == "pull_request"


def test_workflow_dispatch_without_cr():
    result = parse_github_event({}, "workflow_dispatch")

    assert result.mode == "skip"


def test_workflow_dispatch_reads_cr_from_inputs():
    result = parse_github_event({"inputs": {"cr_id": "CR-003"}}, "workflow_dispatch")

    assert result.cr_id == "CR-003"
    assert result.mode == "new"


def test_pull_request_merged_with_cr_in_branch():
    result = parse_github_event({
        "pull_request": {
            "head": {"ref": "cr/CR-034"},
            "merged": True,
            "merge_commit_sha": "abc123",
            "number": 12,
        },
    }, "pull_request", changed_files=_no_git)

    assert result.cr_id == "CR-034"
    assert result.mode == "new"
    assert result.branch_ref == "cr/CR-034"
    assert result.merged is True


def test_pull_request_merged_falls_back_to_the_merge_commit_when_branch_has_no_cr():
    seen = []

    def files(sha: str) -> str:
        seen.append(sha)
        return "DHF/items/00_cr/CR-099.yaml\nsrc/app.py\n"

    result = parse_github_event({
        "pull_request": {
            "head": {"ref": "feature/new-work"},
            "merged": True,
            "merge_commit_sha": "abc123",
            "number": 12,
        },
    }, "pull_request", changed_files=files)

    assert seen == ["abc123"]
    assert result.cr_id == "CR-099"
    assert result.mode == "new"


def test_pull_request_merged_with_no_cr_anywhere_is_skipped():
    result = parse_github_event({
        "pull_request": {
            "head": {"ref": "feature/new-work"},
            "merged": True,
            "merge_commit_sha": "abc123",
        },
    }, "pull_request", changed_files=lambda sha: "README.md\n")

    assert result.cr_id is None
    assert result.mode == "skip"
    assert result.reason == "No CR ID in merged PR"


def test_pull_request_not_merged_spec_branch():
    result = parse_github_event({
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "merged": False,
            "number": 12,
        },
    }, "pull_request")

    assert result.cr_id == "CR-034"
    assert result.mode == "cancel"


def test_pull_request_not_merged_other_branch_is_skipped_with_its_number():
    result = parse_github_event({
        "pull_request": {"head": {"ref": "fix/CR-034"}, "number": 12},
    }, "pull_request")

    assert result.cr_id == "CR-034"
    assert result.mode == "skip"
    assert result.pr_number == 12


def test_pull_request_review_changes_requested():
    result = parse_github_event({
        "review": {"state": "changes_requested"},
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "number": 12,
        },
    }, "pull_request_review")

    assert result.cr_id == "CR-034"
    assert result.mode == "iterate"
    assert result.pr_number == 12
    assert result.review_state == "changes_requested"


def test_pull_request_review_not_changes_requested():
    result = parse_github_event({
        "review": {"state": "approved"},
        "pull_request": {
            "head": {"ref": "spec/CR-034"},
            "number": 12,
        },
    }, "pull_request_review")

    assert result.mode == "skip"
    assert result.pr_number == 12


def test_pull_request_review_without_cr_is_skipped():
    result = parse_github_event({
        "review": {"state": "approved"},
        "pull_request": {"head": {"ref": "main"}, "number": 12},
    }, "pull_request_review")

    assert result.cr_id is None
    assert result.reason == "No CR ID in PR branch"


def test_issue_comment_on_pull_request_extracts_cr_and_labels():
    result = parse_github_event({
        "issue": {
            "number": 21,
            "title": "CR-034 Spec review",
            "pull_request": {"url": "https://api.github.com/repos/acme/repo/pulls/21"},
            "labels": [{"name": "cr:stage/spec"}],
        },
        "comment": {"body": "/approve"},
    }, "issue_comment")

    assert result.cr_id == "CR-034"
    assert result.pr_number == 21
    assert result.mode == "skip"
    assert result.labels == ("cr:stage/spec",)


def test_issue_comment_falls_back_to_the_comment_body():
    result = parse_github_event({
        "issue": {"number": 21, "title": "Spec review",
                  "pull_request": {"url": "u"}},
        "comment": {"body": "/approve CR-035"},
    }, "issue_comment")

    assert result.cr_id == "CR-035"


def test_issue_comment_on_issue_is_skipped():
    result = parse_github_event({
        "issue": {
            "number": 22,
            "title": "CR-035 question",
        },
        "comment": {"body": "/approve"},
    }, "issue_comment")

    assert result.cr_id is None
    assert result.mode == "skip"
    assert "not on a pull request" in result.reason


def test_repository_dispatch():
    result = parse_github_event({
        "client_payload": {"cr_id": "CR-034"},
    }, "repository_dispatch")

    assert result.cr_id == "CR-034"
    assert result.mode == "new"


def test_unhandled_event():
    result = parse_github_event({}, "push")

    assert result.mode == "skip"
    assert result.reason == "Unhandled event: push"


def test_parse_includes_labels_and_dispatch_stage():
    result = parse_github_event({
        "inputs": {
            "cr_id": "CR-010",
            "stage": "spec",
        },
        "pull_request": {
            "head": {"ref": "feat/CR-010"},
            "labels": [{"name": "cr:stage/design"}],
        },
    }, "workflow_dispatch")

    assert result.cr_id == "CR-010"
    assert result.dispatch_stage == "spec"
    assert result.labels == ("cr:stage/design",)


def test_infer_stage_from_label_prefix():
    context = GitHubEventContext(
        cr_id="CR-050",
        mode="skip",
        branch_ref="feat/CR-050",
        labels=("cr:stage/design",),
    )
    assert infer_stage(
        context,
        branch_stage_pairs=(("feat/", "develop"),),
        stage_label_prefix="cr:stage/",
    ) == "design"


def test_infer_stage_from_branch_prefix():
    context = GitHubEventContext(
        cr_id="CR-050",
        mode="skip",
        branch_ref="spec/CR-050",
    )
    assert infer_stage(
        context,
        branch_stage_pairs=(("spec/", "spec"), ("feat/", "develop")),
    ) == "spec"


def test_plan_review_action_uses_stage_label_config():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="iterate",
        pr_number=12,
        event_name="pull_request_review",
        branch_ref="feat/CR-034",
        review_state="approved",
        labels=("cr:stage/spec",),
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("feat/", "develop"),),
        stage_label_prefix="cr:stage/",
        review_actions={"approved:spec": "gen-design"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "gen-design"


def test_plan_review_action_falls_back_to_state_only():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="iterate",
        pr_number=12,
        event_name="pull_request_review",
        branch_ref="spec/CR-034",
        review_state="changes_requested",
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("spec/", "spec"),),
        review_actions={"changes_requested": "revise"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "revise"


def test_plan_dispatch_action_uses_manual_stage():
    context = GitHubEventContext(
        cr_id="CR-100",
        mode="new",
        event_name="workflow_dispatch",
    )

    plan = plan_github_event(
        context,
        manual_stage="design",
        dispatch_actions={"design": "gen-code"},
        default_action="noop",
    )

    assert plan.stage == "design"
    assert plan.action == "gen-code"


def test_plan_pr_action_handles_merged_stage():
    context = GitHubEventContext(
        cr_id="CR-100",
        mode="new",
        event_name="pull_request",
        branch_ref="spec/CR-100",
        merged=True,
    )

    plan = plan_github_event(
        context,
        branch_stage_pairs=(("spec/", "spec"),),
        pr_actions={"merged:spec": "advance-to-design"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "advance-to-design"


def test_plan_issue_comment_uses_stage_label_config():
    context = GitHubEventContext(
        cr_id="CR-034",
        mode="skip",
        pr_number=21,
        event_name="issue_comment",
        labels=("cr:stage/spec",),
    )

    plan = plan_github_event(
        context,
        stage_label_prefix="cr:stage/",
        dispatch_actions={"spec": "record-approval"},
        default_action="noop",
    )

    assert plan.stage == "spec"
    assert plan.action == "record-approval"


# ── What the docs tell a caller to branch on ──────────────────────────────────


class TestActionIsTheVerdictAndModeIsTheFallback:
    """`--help` and the README say: branch on `action`, never on `mode`.

    They are two vocabularies, not one. `mode` is this tool's own reading of the
    event — a fixed `new`/`iterate`/`cancel`/`skip` — and `action` is whatever
    the caller's mappings name, falling back to `mode` when none matches. Seeing
    them differ in one payload reads as a contradiction until you know that; it
    is the normal case, and it is why the two fields are now explained where a
    caller meets them.
    """

    def _context(self) -> GitHubEventContext:
        return GitHubEventContext(
            cr_id="CR-007",
            mode="skip",
            pr_number=42,
            event_name="pull_request_review",
            branch_ref="feat/CR-007",
            review_state="approved",
        )

    def test_action_falls_back_to_mode_when_nothing_maps(self):
        plan = plan_github_event(
            self._context(), branch_stage_pairs=(("feat/", "develop"),),
        )
        assert plan.action == "skip", (
            "with no mapping and no --default-action, `action` must be `mode`, "
            "so a caller branching on `action` alone still gets an answer"
        )

    def test_a_mapping_overrides_mode_without_rewriting_it(self):
        plan = plan_github_event(
            self._context(),
            branch_stage_pairs=(("feat/", "develop"),),
            review_actions={"approved": "advance"},
        )
        assert plan.action == "advance", "the caller's mapping must win"
        assert self._context().mode == "skip", (
            "`mode` is this tool's own reading; a caller's mapping must not "
            "rewrite it"
        )
        assert plan.action != self._context().mode, (
            "this is the case that reads as a contradiction until the docs "
            "explain it; if the two stop differing the fixture stops testing it"
        )

    def test_default_action_also_displaces_mode(self):
        plan = plan_github_event(
            self._context(), branch_stage_pairs=(("feat/", "develop"),),
            default_action="noop",
        )
        assert plan.action == "noop" and self._context().mode == "skip"
