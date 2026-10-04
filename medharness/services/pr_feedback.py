"""What a reviewer asked for on a PR, putting a run's work back on it, and the session a revision resumes."""

from __future__ import annotations

import json
from pathlib import Path

from medharness.services import git
from medharness.services.gh import gh
from medharness.services.stage_run import _begin_step, _finish_step, _warning


def _pr_base(pr_number: int) -> str | None:
    """The branch the PR targets, as a remote ref; None when GitHub will not say."""
    rc, base = gh(["pr", "view", str(pr_number), "--json", "baseRefName", "-q", ".baseRefName"])
    return f"origin/{base}" if rc == 0 and base else None


def _pr_feedback(pr_number: int, steps: list, diagnostics: dict, warnings: list) -> dict | None:
    """The PR's review feedback, or None when it has none to act on.

    `--pr` says the run belongs to that PR; it revises only when a reviewer has
    asked for a change on the current commit, so a new or approved PR generates.
    """
    step, perf = _begin_step("fetch_pr_feedback")
    feedback = _get_pr_feedback(pr_number)
    diagnostics["github_feedback"] = feedback["diagnostics"]
    warnings.extend(feedback["warnings"])
    steps.append(_finish_step(step, perf, "warning" if feedback["warnings"] else "ok",
                              feedback["diagnostics"]))
    said = feedback["diagnostics"]["comments_count"] + feedback["diagnostics"]["reviews_count"]
    return feedback if said else None


def _push_to_pr(repo_root: Path, pr_number: int, message: str, errors: list[dict]) -> None:
    """Commit the run's work and push it to the PR's branch."""
    rc, branch = gh(["pr", "view", str(pr_number), "--json", "headRefName", "-q", ".headRefName"])
    if rc != 0 or not branch:
        errors.append({"field": "pr_push", "issue": f"PR #{pr_number}'s branch could not be read: {branch}",
                       "fix": "Check GH_TOKEN and that the PR exists."})
        return
    problem = git.commit_and_push(repo_root, message, branch)
    if problem:
        errors.append({"field": "pr_push", "issue": f"The run's work did not reach PR #{pr_number}: {problem}",
                       "fix": "Commit and push the working tree by hand; nothing was lost locally."})


def _get_pr_feedback(pr_number: int) -> dict:
    """What reviewers asked to change on the PR's current commit, via gh.

    An approval asks for nothing, and a review of an earlier commit was about
    code that has since changed; neither is feedback to revise from. What is:
    a review requesting changes, or a review with something to say — a body or
    inline comments — on the commit the PR now points at.
    """

    def _fetch(kind: str, path: str) -> dict[str, object]:
        rc, out = gh(["api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}{path}"])
        if rc != 0:
            return {
                "status": "gh_error",
                "data": [],
                "error": out,
                "warning": _warning(f"github_{kind}_unavailable", f"GitHub {kind} fetch failed: {out}."),
            }
        try:
            return {"status": "ok", "data": json.loads(out or "[]"), "error": None}
        except json.JSONDecodeError as exc:
            return {
                "status": "decode_error",
                "data": [],
                "error": str(exc),
                "warning": _warning(f"github_{kind}_decode_error",
                                    f"GitHub {kind} response could not be decoded: {exc}."),
            }

    pull = _fetch("pull", "")
    comments = _fetch("comments", "/comments")
    reviews = _fetch("reviews", "/reviews")
    head = (pull["data"] or {}).get("head", {}).get("sha") if isinstance(pull["data"], dict) else None

    with_comments = {c.get("pull_request_review_id") for c in comments["data"] if isinstance(c, dict)}
    asked = [
        r for r in reviews["data"]
        if isinstance(r, dict)
        and (head is None or r.get("commit_id") == head)
        and (r.get("state") == "CHANGES_REQUESTED"
             or (r.get("state") == "COMMENTED"
                 and ((r.get("body") or "").strip() or r.get("id") in with_comments)))
    ]
    asked_ids = {r.get("id") for r in asked}
    asked_comments = [c for c in comments["data"]
                      if isinstance(c, dict) and c.get("pull_request_review_id") in asked_ids]
    return {
        "prompt_text": json.dumps({"reviews": asked, "comments": asked_comments}, indent=2),
        "diagnostics": {
            "attempted": True,
            "pr_number": pr_number,
            "head_sha": head,
            "comments_status": comments["status"],
            "comments_error": comments["error"],
            "reviews_status": reviews["status"],
            "reviews_error": reviews["error"],
            "comments_count": len(asked_comments),
            "reviews_count": len(asked),
        },
        "warnings": [w for w in (pull.get("warning"), comments.get("warning"), reviews.get("warning"))
                     if isinstance(w, dict)],
    }


def _auto_post_pr_feedback(pr_number: int, cr_id: str, result: dict, *, token: str = "") -> list[str]:
    """Post warning and error comments to the PR. Returns list of posted comment URLs."""
    comments: list[str] = []

    warnings = result.get("warnings") or []
    if warnings:
        lines = "\n".join(
            f"- `{w.get('code', '?')}`: {w.get('message', '')}" for w in warnings
        )
        url = post_pr_comment(pr_number, f"⚠️ **Warnings for {cr_id}:**\n\n{lines}", token=token)
        if url:
            comments.append(url)

    errors = result.get("errors") or []
    if result.get("outcome") == "completed_with_errors" and errors:
        lines = "\n".join(
            f"- **{e.get('field', '?')}**: {e.get('issue', '')}\n  _Fix:_ {e.get('fix', '')}"
            for e in errors
        )
        url = post_pr_comment(
            pr_number,
            f"⚠️ **Validation errors for {cr_id}:**\n\n{lines}",
            token=token,
        )
        if url:
            comments.append(url)

    return comments


def post_pr_comment(pr_number: int | str, body: str, *, token: str = "") -> str:
    """Post a comment on a PR. Returns the comment URL or empty string on failure."""
    rc, out = gh(["pr", "comment", str(pr_number), "--body", body], token=token, timeout=15)
    return out if rc == 0 else ""


_MARKER_START = "<!-- claude-session:"
_MARKER_END = "-->"


def put_session(pr_number: int | str, session_id: str, *, token: str = "") -> str:
    """Store a Claude session ID as a PR comment marker.

    Returns the URL of the comment (or empty string on failure).
    """
    body = f"{_MARKER_START} {session_id} {_MARKER_END}"
    rc, out = gh(["pr", "comment", str(pr_number), "--body", body], token=token, timeout=15)
    return out if rc == 0 else ""


def get_session(pr_number: int | str, *, token: str = "") -> str:
    """Retrieve the last stored Claude session ID from PR comments.

    Returns the session ID string (empty if not found).
    """
    rc, out = gh(
        [
            "pr", "view", str(pr_number),
            "--json", "comments",
            "--jq",
            f'[.comments[].body | select(startswith("{_MARKER_START}"))] | last // empty | ltrimstr("{_MARKER_START} ") | rtrimstr(" {_MARKER_END}")',
        ],
        token=token, timeout=15,
    )
    return out if rc == 0 and out != "null" else ""
