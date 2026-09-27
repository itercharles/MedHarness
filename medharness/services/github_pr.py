"""GitHub PR operations — comment posting via gh CLI."""

from __future__ import annotations

from medharness.services.gh import gh


def post_pr_comment(pr_number: int | str, body: str, *, token: str = "") -> str:
    """Post a comment on a PR. Returns the comment URL or empty string on failure."""
    rc, out = gh(["pr", "comment", str(pr_number), "--body", body], token=token, timeout=15)
    return out if rc == 0 else ""
