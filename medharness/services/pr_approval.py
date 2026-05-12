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


def check_approved(pr_number: int | str, stage: str, *, token: str = "") -> bool:
    """Check whether the stage approval label is present on the PR."""
    label = label_for_stage(stage)
    if not label:
        return False
    rc, output = _gh(
        [
            "pr", "view", str(pr_number),
            "--json", "labels",
            "--jq", f'[.labels[].name] | contains(["{label}"])',
        ],
        token=token,
    )
    return rc == 0 and output.strip() == "true"
