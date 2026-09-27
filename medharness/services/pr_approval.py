"""PR approval: an approving review of the commit being merged.

A GitHub review carries an author, a time, and the commit it approved. A label
carries none of those and anyone with write access can move it, so the gate
reads reviews and pins them to the PR's head commit.
"""

from __future__ import annotations

import json

from medharness.services.gh import gh


def _pr_head_sha(pr_number: int | str, *, token: str = "") -> str:
    rc, out = gh(
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
    rc, out = gh(
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
    """What approves this pull request, read from GitHub. See ``judge_approval``."""
    return judge_approval(
        _pr_head_sha(pr_number, token=token), _reviews(pr_number, token=token),
    )


def judge_approval(head_sha: str, reviews: list[dict] | None) -> dict:
    """What approves a pull request at *head_sha*, and whether it still applies.

    *reviews* are ``{state, commit_id, login, submitted_at}`` dicts, or None
    when they could not be read.

    A GitHub label was the old answer. Anyone with write access can add or
    remove one, it carries no author, no time, and no revision — so it records
    that someone clicked, not that anyone reviewed. A review carries all three,
    and naming the commit is what makes it evidence: approval of work that has
    since changed is not approval of what ships.

    There is no stage to pass: the commit is what separates them. A design
    approval covers the cascade that was the head at the time and goes stale
    the moment the code lands, so the develop gate needs its own review.
    """
    if reviews is None:
        return {
            "approved": False,
            "reason": "the pull request's reviews could not be read",
            "head_sha": head_sha,
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
        (approvals if head_sha and r.get("commit_id") == head_sha else stale).append(entry)

    if approvals:
        reason = ""
    elif stale:
        reason = "every approving review is against an earlier commit"
    else:
        reason = "no approving review"
    return {
        "approved": bool(approvals),
        "reason": reason,
        "head_sha": head_sha,
        "approvals": approvals,
        "stale_approvals": stale,
    }
