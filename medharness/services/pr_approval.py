"""PR approval gate — parse /approve and /reject commands from PR comments.

Provides a machine-readable approval mechanism that replaces the implicit
"merging = approval" convention with an explicit command-and-label scheme.

Label scheme:
    cr-spec-approved   — spec approved, ready for design stage
    cr-design-approved — design approved, ready for develop stage
    cr-code-approved   — code approved, ready to merge

Commands (typed in PR comments):
    /approve           — adds the stage label and posts confirmation
    /reject <reason>   — posts rejection comment and closes the PR
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field


_APPROVE_RE = re.compile(r"^\s*/approve\s*$", re.MULTILINE | re.IGNORECASE)
_REJECT_RE = re.compile(r"^\s*/reject(?:\s+(.+))?$", re.MULTILINE | re.IGNORECASE)

_STAGE_LABELS: dict[str, str] = {
    "spec": "cr-spec-approved",
    "design": "cr-design-approved",
    "develop": "cr-code-approved",
}

_BRANCH_STAGE: dict[str, str] = {
    "spec/": "spec",
    "design/": "design",
    "feat/": "develop",
}


@dataclass(frozen=True)
class ApprovalCommand:
    action: str  # "approve" | "reject"
    reason: str = field(default="")


def parse_approval_command(comment_body: str) -> ApprovalCommand | None:
    """Parse a PR comment body for /approve or /reject commands.

    Returns an ApprovalCommand if a command is found, None otherwise.
    Only the first command found is returned (approve takes priority).
    """
    if _APPROVE_RE.search(comment_body):
        return ApprovalCommand(action="approve")
    m = _REJECT_RE.search(comment_body)
    if m:
        reason = (m.group(1) or "").strip()
        return ApprovalCommand(action="reject", reason=reason)
    return None


def label_for_stage(stage: str) -> str | None:
    """Return the GitHub label name for a CR stage, or None for unknown stages."""
    return _STAGE_LABELS.get(stage)


def stage_for_branch(branch_ref: str) -> str | None:
    """Infer approval stage from a branch name prefix."""
    for prefix, stage in _BRANCH_STAGE.items():
        if branch_ref.startswith(prefix):
            return stage
    return None


def _gh(args: list[str], *, token: str = "") -> tuple[int, str]:
    env = {**os.environ}
    gh_token = token or os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token
    try:
        result = subprocess.run(  # noqa: S603
            ["gh", *args], capture_output=True, text=True, env=env, timeout=30,
        )
        return result.returncode, result.stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, str(exc)


def add_approval_label(pr_number: int | str, stage: str, *, token: str = "") -> bool:
    """Add the stage approval label to the PR. Returns True on success."""
    label = label_for_stage(stage)
    if not label:
        return False
    rc, _ = _gh(["pr", "edit", str(pr_number), "--add-label", label], token=token)
    return rc == 0


def post_comment(pr_number: int | str, body: str, *, token: str = "") -> bool:
    """Post a comment to the PR. Returns True on success."""
    rc, _ = _gh(["pr", "comment", str(pr_number), "--body", body], token=token)
    return rc == 0


def close_pr(pr_number: int | str, *, token: str = "") -> bool:
    """Close the PR without merging. Returns True on success."""
    rc, _ = _gh(["pr", "close", str(pr_number)], token=token)
    return rc == 0


def _pr_head_sha(pr_number: int | str, *, token: str = "") -> str:
    rc, out = _gh(
        ["pr", "view", str(pr_number), "--json", "headRefOid", "--jq", ".headRefOid"],
        token=token,
    )
    return out.strip() if rc == 0 else ""


def _reviews(pr_number: int | str, *, token: str = "") -> list[dict] | None:
    """Reviews with the commit each one approved, or None when unreadable.

    The REST endpoint rather than `gh pr view --json reviews`, which omits
    `commit_id` — and a review that does not say what it reviewed is no better
    than a label.
    """
    rc, out = _gh(
        ["api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews",
         "--paginate", "--jq",
         '[.[] | {state, commit_id, login: .user.login, submitted_at}]'],
        token=token,
    )
    if rc != 0:
        return None
    try:
        payload = json.loads(out or "[]")
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, list) else None


def approval_evidence(pr_number: int | str, stage: str, *, token: str = "") -> dict:
    """What approves this stage, and whether it still applies.

    A GitHub label was the old answer. Anyone with write access can add or
    remove one, it carries no author, no time, and no revision — so it records
    that someone clicked, not that anyone reviewed. A review carries all three,
    and naming the commit is what makes it evidence: approval of work that has
    since changed is not approval of what ships.
    """
    head = _pr_head_sha(pr_number, token=token)
    reviews = _reviews(pr_number, token=token)
    if reviews is None:
        return {
            "approved": False,
            "reason": "the pull request's reviews could not be read",
            "head_sha": head,
            "approvals": [],
            "stale_approvals": [],
        }

    approvals, stale = [], []
    for r in reviews:
        if str(r.get("state", "")).upper() != "APPROVED":
            continue
        entry = {
            "by": r.get("login"),
            "at": r.get("submitted_at"),
            "commit": r.get("commit_id"),
        }
        # An unreadable commit counts as stale: the gate must not pass on an
        # approval it cannot tie to what is being merged.
        (approvals if head and r.get("commit_id") == head else stale).append(entry)

    if approvals:
        reason = ""
    elif stale:
        reason = "every approving review is against an earlier commit"
    else:
        reason = "no approving review"
    return {
        "approved": bool(approvals),
        "reason": reason,
        "head_sha": head,
        "approvals": approvals,
        "stale_approvals": stale,
    }


def check_approved(pr_number: int | str, stage: str, *, token: str = "") -> bool:
    """Whether an approving review covers the commit this PR would merge."""
    return approval_evidence(pr_number, stage, token=token)["approved"]
