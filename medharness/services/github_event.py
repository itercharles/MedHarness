"""Parse GitHub event payloads to extract CR context for CI workflows.

Reads $GITHUB_EVENT_PATH and extracts CR ID, mode (new/iterate/cancel), and
optional PR number. Designed for one-liner workflow usage.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitHubEventContext:
    cr_id: str | None
    mode: str  # "new", "iterate", "cancel", "skip"
    pr_number: int | None = None
    reason: str = ""


_CR_RE = re.compile(r"CR-\d+")


def parse_github_event(
    event_path: Path | None = None,
    *,
    manual_cr_id: str = "",
    head_ref: str | None = None,
    merged: bool | None = None,
    merge_commit_sha: str | None = None,
) -> GitHubEventContext:
    """Parse a GitHub Actions event payload and return CR workflow context.

    If *event_path* is omitted, reads ``$GITHUB_EVENT_PATH``.  Additional
    kwargs are only needed when the caller already has extracted values and
    wants to avoid re-reading the event file.
    """
    event_path = event_path or Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    event: dict = {}
    if event_path.exists():
        try:
            event = json.loads(event_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if head_ref is None:
        head_ref = (event.get("pull_request", {}) or {}).get("head", {}).get("ref", "")
    if merged is None:
        merged = bool((event.get("pull_request", {}) or {}).get("merged", False))

    # -- workflow_dispatch --------------------------------------------------
    if event_name == "workflow_dispatch" or manual_cr_id:
        cr_id = manual_cr_id or (event.get("inputs", {}) or {}).get("cr_id", "")
        if cr_id:
            return GitHubEventContext(cr_id=cr_id, mode="new")
        return GitHubEventContext(cr_id=None, mode="skip", reason="No cr_id input")

    # -- pull_request -------------------------------------------------------
    if event_name == "pull_request":
        if merged:
            # Merged PR: extract CR from branch name → new design/spec/impl
            cr_id = _extract_cr(head_ref)
            if not cr_id and merge_commit_sha:
                # Fallback: git diff the merge commit
                cr_id = _extract_cr_from_diff(merge_commit_sha)
            if cr_id:
                return GitHubEventContext(cr_id=cr_id, mode="new")
            return GitHubEventContext(cr_id=None, mode="skip", reason="No CR ID in merged PR")

        # Open or closed (not merged) PR
        if head_ref.startswith(("spec/", "design/", "feat/")):
            cr_id = _extract_cr(head_ref)
            if not merged:
                return GitHubEventContext(cr_id=cr_id, mode="cancel" if cr_id else "skip")
            return GitHubEventContext(cr_id=cr_id, mode="new")

        pr_number = (event.get("pull_request", {}) or {}).get("number")
        return GitHubEventContext(
            cr_id=_extract_cr(head_ref),
            mode="skip",
            pr_number=pr_number,
            reason="PR not merged and branch not spec/design/feat prefix",
        )

    # -- pull_request_review ------------------------------------------------
    if event_name == "pull_request_review":
        review = event.get("review", {}) or {}
        pr_info = event.get("pull_request", {}) or {}
        head_ref = pr_info.get("head", {}).get("ref", "")
        cr_id = _extract_cr(head_ref)
        if not cr_id:
            return GitHubEventContext(cr_id=None, mode="skip", reason="No CR ID in PR branch")
        if review.get("state") == "changes_requested":
            return GitHubEventContext(
                cr_id=cr_id, mode="iterate",
                pr_number=pr_info.get("number"),
            )
        return GitHubEventContext(cr_id=cr_id, mode="skip", reason="Review not changes_requested")

    # -- repository_dispatch ------------------------------------------------
    if event_name == "repository_dispatch":
        cr_id = (event.get("client_payload", {}) or {}).get("cr_id", "")
        if cr_id:
            return GitHubEventContext(cr_id=cr_id, mode="new")
        return GitHubEventContext(cr_id=None, mode="skip", reason="No cr_id in dispatch payload")

    return GitHubEventContext(cr_id=None, mode="skip", reason=f"Unhandled event: {event_name}")


def _extract_cr(text: str) -> str | None:
    m = _CR_RE.search(text or "")
    return m.group(0) if m else None


def _extract_cr_from_diff(sha: str) -> str | None:
    """Try to extract a CR ID from a git diff of a merge commit."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{sha}~1", sha],
            capture_output=True, text=True, timeout=10,
        )
        return _extract_cr(result.stdout)
    except Exception:
        return None
