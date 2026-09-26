"""PR approval: an approving review of the commit being merged.

A GitHub review carries an author, a time, and the commit it approved. A label
carries none of those and anyone with write access can move it, so the gate
reads reviews and pins them to the PR's head commit.
"""

from __future__ import annotations

import json
import os
import subprocess


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


def approval_evidence(pr_number: int | str, *, token: str = "") -> dict:
    """What approves this pull request, and whether it still applies.

    A GitHub label was the old answer. Anyone with write access can add or
    remove one, it carries no author, no time, and no revision — so it records
    that someone clicked, not that anyone reviewed. A review carries all three,
    and naming the commit is what makes it evidence: approval of work that has
    since changed is not approval of what ships.

    There is no stage to pass: the commit is what separates them. A design
    approval covers the cascade that was the head at the time and goes stale
    the moment the code lands, so the develop gate needs its own review.
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

