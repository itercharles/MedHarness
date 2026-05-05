"""CR workflow commands — Click declarations + presentation only."""

import json
from pathlib import Path
import click


def register(main):
    from medharness.commands.cr import (
        workflow_complete, workflow_intake_github_issue,
        workflow_intake_github_issue_ci, workflow_complete_from_github_pr,
        check_status,
    )

    @main.group()
    def cr() -> None:
        """Commands for Change Request git-evidence management."""

    @cr.group("workflow")
    def cr_workflow() -> None:
        """Reusable CR workflow orchestration commands."""

    @cr_workflow.command("complete")
    @click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--cr", "cr_id", required=True, metavar="CR_ID")
    @click.option("--by", "performed_by", default="medharness", show_default=True)
    @click.option("--commit/--no-commit", "commit_changes", default=True, show_default=True)
    @click.option("--push", is_flag=True, default=False)
    @click.option("--message", default=None, metavar="TEXT")
    @click.pass_context
    def cr_workflow_complete(ctx: click.Context, dhf_repo: Path | None, cr_id: str,
                              performed_by: str, commit_changes: bool, push: bool,
                              message: str | None) -> None:
        """Complete a CR in a DHF repository after implementation merge."""
        click.echo(json.dumps(workflow_complete(
            ctx, dhf_repo, cr_id, performed_by, commit_changes, push, message,
        ), default=str))

    @cr_workflow.command("intake-github-issue")
    @click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--event", "event_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--comments", "comments_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--active-milestone", default=None)
    @click.option("--marker-name", default="medharness-cr", show_default=True)
    @click.option("--branch-prefix", default="cr", show_default=True)
    @click.option("--title-prefix", default="cr", show_default=True)
    @click.option("--write", is_flag=True, default=False)
    @click.option("--output", type=click.Path(dir_okay=False, path_type=Path))
    @click.pass_context
    def cr_workflow_intake_github_issue(ctx: click.Context, dhf_repo: Path | None,
                                         event_path: Path, comments_path: Path | None,
                                         active_milestone: str | None, marker_name: str,
                                         branch_prefix: str, title_prefix: str,
                                         write: bool, output: Path | None) -> None:
        """Prepare a CR from a GitHub issue event."""
        payload = workflow_intake_github_issue(
            ctx, dhf_repo, event_path, comments_path, active_milestone,
            marker_name, branch_prefix, title_prefix, write,
        )
        text = json.dumps(payload, indent=2)
        if output:
            output.write_text(text + "\n", encoding="utf-8")
        click.echo(text)

    @cr_workflow.command("intake-github-issue-ci")
    @click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--event", "event_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--comments", "comments_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--active-milestone", default=None)
    @click.option("--marker-name", default="medharness-cr", show_default=True)
    @click.option("--branch-prefix", default="cr", show_default=True)
    @click.option("--title-prefix", default="cr", show_default=True)
    @click.option("--write", is_flag=True, default=False)
    @click.option("--create-branch", is_flag=True, default=False)
    @click.option("--open-pr", is_flag=True, default=False)
    @click.option("--source-repo", default=None, metavar="OWNER/REPO")
    @click.option("--comment-source-issue", is_flag=True, default=False)
    @click.option("--issue-number", type=int, default=None)
    @click.option("--github-token", default=None, metavar="TOKEN")
    @click.option("--milestone-title", default=None, metavar="TITLE")
    @click.option("--output", type=click.Path(dir_okay=False, path_type=Path))
    @click.option("--github-output", type=click.Path(dir_okay=False, path_type=Path))
    @click.pass_context
    def cr_workflow_intake_github_issue_ci(ctx: click.Context, dhf_repo: Path | None,
                                            event_path: Path, comments_path: Path | None,
                                            active_milestone: str | None, marker_name: str,
                                            branch_prefix: str, title_prefix: str,
                                            write: bool, create_branch: bool, open_pr: bool,
                                            source_repo: str | None, comment_source_issue: bool,
                                            issue_number: int | None, github_token: str | None,
                                            milestone_title: str | None, output: Path | None,
                                            github_output: Path | None) -> None:
        """Full CI intake pipeline: prepare CR + GitHub plumbing."""
        payload = workflow_intake_github_issue_ci(
            ctx, dhf_repo, event_path, comments_path, active_milestone,
            marker_name, branch_prefix, title_prefix, write, create_branch,
            open_pr, source_repo, comment_source_issue, issue_number,
            github_token, milestone_title,
        )
        text = json.dumps(payload, indent=2)
        if output:
            output.write_text(text + "\n", encoding="utf-8")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f_out:
                for key, value in payload.items():
                    val = str(value) if value is not None else ""
                    if isinstance(value, bool):
                        val = str(value).lower()
                    f_out.write(f"{key}={val}\n")
        click.echo(text)

    @cr_workflow.command("complete-from-github-pr")
    @click.option("--dhf-repo", type=click.Path(file_okay=False, path_type=Path))
    @click.option("--event", "event_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
    @click.option("--pr-title", default=None, metavar="TITLE")
    @click.option("--by", "performed_by", default="medharness", show_default=True)
    @click.option("--push", is_flag=True, default=False)
    @click.option("--message", default=None, metavar="TEXT")
    @click.pass_context
    def cr_workflow_complete_from_github_pr(ctx: click.Context, dhf_repo: Path | None,
                                             event_path: Path | None, pr_title: str | None,
                                             performed_by: str, push: bool,
                                             message: str | None) -> None:
        """Complete a CR from a merged GitHub PR event."""
        result = workflow_complete_from_github_pr(
            ctx, dhf_repo, event_path, pr_title, performed_by, push, message,
        )
        if result:
            if result.get("skip"):
                reason = result.get("reason", "skipped")
                click.echo(json.dumps(result), err=("SKIP" in reason))
                if result.get("status"):
                    click.echo(f"SKIP: {result['cr_id']} is already '{result['status']}' — nothing to do.", err=True)
            else:
                click.echo(json.dumps(result, default=str))

    @cr.command("check-status")
    @click.argument("cr_id")
    @click.pass_context
    def cr_check_status(ctx: click.Context, cr_id: str) -> None:
        """Check that a Change Request exists and is in an authorized state.

        CR_ID is the identifier of the change request (e.g. CR-012).
        Outputs a JSON object to stdout. Exits 0 if valid, 1 otherwise.
        """
        import sys
        result = check_status(ctx, cr_id)
        click.echo(json.dumps(result, default=str))
        if result["found"] and result["valid"]:
            click.echo(f"✓ CR '{cr_id}' is authorized (status: {result['status']}).", err=True)
        else:
            if not result["found"]:
                click.echo(f"ERROR: CR '{cr_id}' not found.", err=True)
            else:
                click.echo(f"✗ CR '{cr_id}' is not authorized: status is '{result['status']}'.", err=True)
            sys.exit(1)

