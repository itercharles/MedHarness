"""CR workflow command handlers — returns data, no CLI output.

ClickException is used only for unrecoverable operational errors (missing CR,
invalid state transitions), not for control-flow decisions like check_status.
"""

import json
import os
import subprocess
import re as _re
from pathlib import Path

import json
import os
import subprocess
import re as _re
from pathlib import Path

import click
import medharness._helpers as _h
from medharness.workflows.cr_intake import (
    current_iso_week_milestone, load_comments,
    load_github_issue_event, prepare_cr_from_issue,
)
from dhfkit.change_requests import complete_change_request


def workflow_complete(
    ctx: click.Context, dhf_repo: Path | None, cr_id: str,
    performed_by: str, commit_changes: bool, push: bool,
    message: str | None,
) -> dict:
    repo_root, dhf_root = _h._resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _h._make_adapter_for_dhf_root(dhf_root)

    try:
        transition = complete_change_request(adapter, cr_id, performed_by=performed_by)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    changed = _h._git_has_changes(repo_root)
    committed = False
    pushed = False
    commit_message = message or f"chore: complete {cr_id} [skip ci]"

    if changed and commit_changes:
        _h._run_git(repo_root, ["add", "-A"])
        if _h._git_has_changes(repo_root):
            _h._run_git(repo_root, ["commit", "-m", commit_message])
            committed = True
            if push:
                _h._run_git(repo_root, ["push"])
                pushed = True

    return {
        "cr_id": cr_id, "dhf_repo": str(repo_root), "dhf_root": str(dhf_root),
        "transition": transition, "changed": changed,
        "committed": committed, "pushed": pushed,
        "commit_message": commit_message if committed else None,
    }


def workflow_intake_github_issue(
    ctx: click.Context, dhf_repo: Path | None, event_path: Path,
    comments_path: Path | None, active_milestone: str | None,
    marker_name: str, branch_prefix: str, title_prefix: str,
    write: bool,
) -> dict:
    _, dhf_root = _h._resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _h._make_adapter_for_dhf_root(dhf_root)
    result = prepare_cr_from_issue(
        load_github_issue_event(event_path),
        active_milestone or current_iso_week_milestone(),
        load_comments(comments_path),
        write=write, adapter=adapter,
        marker_name=marker_name, branch_prefix=branch_prefix, title_prefix=title_prefix,
    )
    return {
        "should_create": result.should_create, "reason": result.reason,
        "cr_id": result.cr_id, "branch": result.branch,
        "cr_path": result.cr_path, "title": result.title,
    }


def workflow_intake_github_issue_ci(
    ctx: click.Context, dhf_repo: Path | None, event_path: Path,
    comments_path: Path | None, active_milestone: str | None,
    marker_name: str, branch_prefix: str, title_prefix: str,
    write: bool, create_branch: bool, open_pr: bool,
    source_repo: str | None, comment_source_issue: bool,
    issue_number: int | None, github_token: str | None,
    milestone_title: str | None,
) -> dict:
    repo_root, dhf_root = _h._resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _h._make_adapter_for_dhf_root(dhf_root)
    gh_token = github_token or os.environ.get("GH_TOKEN") or ""
    source_token = os.environ.get("GITHUB_TOKEN") or gh_token
    gh_env = _h._github_env(gh_token)

    event = load_github_issue_event(event_path)
    issue_num = issue_number or event.number
    src_repo = source_repo or os.environ.get("GITHUB_REPOSITORY", "")
    milestone = milestone_title or event.milestone or ""

    result = prepare_cr_from_issue(
        event, active_milestone or current_iso_week_milestone(),
        _h._load_issue_comments(comments_path, source_repo=src_repo,
                                issue_number=issue_num, source_token=source_token),
        write=write, adapter=adapter,
        marker_name=marker_name, branch_prefix=branch_prefix, title_prefix=title_prefix,
    )

    branch_url = ""
    pr_url = ""
    if result.should_create and write:
        branch = result.branch
        if create_branch:
            _h._run_git(repo_root, ["checkout", "-B", branch])
            _h._run_git(repo_root, ["add", "-A"])
            if _h._git_has_changes(repo_root):
                _h._run_git(repo_root, ["commit", "-m", f"cr: create {result.cr_id} from issue"])
                _h._run_git(repo_root, ["push", "--force", "--set-upstream", "origin", branch])

        if open_pr and src_repo:
            try:
                existing = subprocess.run(
                    [
                        "gh", "pr", "list", "--repo", src_repo,
                        "--head", branch, "--json", "url", "--jq", ".[0].url",
                    ],
                    cwd=repo_root, capture_output=True, text=True, env=gh_env,
                )
                if existing.returncode != 0:
                    message = (existing.stderr or existing.stdout).strip()
                    raise click.ClickException(
                        message or f"failed to list PRs for branch {branch}"
                    )
                if existing.stdout.strip():
                    pr_url = existing.stdout.strip()
                else:
                    body = (
                        f"Automated CR intake from {src_repo} issue:\n\n"
                        f"- Source issue: {event.html_url}\n"
                        f"- Target weekly milestone: {milestone}\n\n"
                        f"This PR creates {result.cr_id}. Human approval is required."
                    )
                    proc = subprocess.run(
                        [
                            "gh", "pr", "create", "--repo", src_repo,
                            "--head", branch, "--base", "main",
                            "--title", result.title, "--body", body,
                        ],
                        cwd=repo_root, capture_output=True, text=True, env=gh_env,
                    )
                    if proc.returncode != 0:
                        message = (proc.stderr or proc.stdout).strip()
                        raise click.ClickException(
                            message or f"failed to create PR for branch {branch}"
                        )
                    pr_url = proc.stdout.strip()
            except FileNotFoundError:
                raise click.ClickException("gh CLI not available — cannot open PR")

        if comment_source_issue and src_repo and issue_num and result.cr_id:
            comment_body = (
                f"CR created from this issue.\n\n"
                f"CR: {result.cr_id}\n"
                f"DHF PR: {pr_url}\n\n"
                f"<!-- {marker_name}: {result.cr_id} -->\n"
                f"<!-- {marker_name}-pr: {pr_url} -->"
            )
            try:
                subprocess.run(
                    ["gh", "issue", "comment", str(issue_num), "--body", comment_body,
                     "--repo", src_repo],
                    capture_output=True, text=True, env=_h._github_env(source_token), check=False,
                )
            except FileNotFoundError:
                pass  # gh CLI not available — skip issue comment

    return {
        "should_create": result.should_create, "reason": result.reason,
        "cr_id": result.cr_id, "branch": result.branch,
        "branch_url": branch_url, "pr_url": pr_url, "title": result.title,
    }


def workflow_complete_from_github_pr(
    ctx: click.Context, dhf_repo: Path | None, event_path: Path | None,
    pr_title: str | None, performed_by: str, push: bool,
    message: str | None,
) -> dict | None:
    title = pr_title or ""
    if not title and event_path:
        try:
            event_data = json.loads(event_path.read_text(encoding="utf-8"))
            title = event_data.get("pull_request", {}).get("title", "")
        except (json.JSONDecodeError, OSError):
            pass

    cr_match = _re.search(r"CR-\d+", title) if title else None
    if not cr_match:
        return {"skip": True, "reason": "No CR ID found in PR title"}

    cr_id = cr_match.group(0)
    repo_root, dhf_root = _h._resolve_dhf_repo_paths(ctx, dhf_repo)
    adapter = _h._make_adapter_for_dhf_root(dhf_root)

    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "GitHub Actions [bot]"],
        capture_output=True, check=False,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email",
         "github-actions[bot]@users.noreply.github.com"],
        capture_output=True, check=False,
    )

    try:
        transition = complete_change_request(adapter, cr_id, performed_by=performed_by)
    except ValueError as exc:
        item = adapter.get_item(cr_id)
        current_status = item.get("status", "unknown") if item else "unknown"
        if current_status in ("completed", "cancelled"):
            return {"skip": True, "cr_id": cr_id, "status": current_status,
                    "reason": f"Already '{current_status}'"}
        raise click.ClickException(str(exc)) from exc

    changed = _h._git_has_changes(repo_root)
    commit_message = message or f"chore: complete {cr_id} [skip ci]"
    committed = False
    pushed = False

    if changed:
        _h._run_git(repo_root, ["add", "-A"])
        if _h._git_has_changes(repo_root):
            _h._run_git(repo_root, ["commit", "-m", commit_message])
            committed = True
            if push:
                _h._run_git(repo_root, ["push"])
                pushed = True

    return {
        "cr_id": cr_id, "pr_title": title, "transition": transition,
        "changed": changed, "committed": committed, "pushed": pushed,
    }


def check_status(ctx: click.Context, cr_id: str) -> dict:
    core = _h._make_core(ctx)
    item = core.get_item(cr_id)
    if item is None:
        return {"cr_id": cr_id, "found": False, "error": f"CR '{cr_id}' not found"}

    status = item.get("status", "")
    valid_statuses = {"new", "analyzing", "developing"}
    return {
        "cr_id": cr_id, "found": True,
        "status": status, "valid": status in valid_statuses,
    }
