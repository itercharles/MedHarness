"""Parse and plan GitHub event payloads for CI workflows.

The core parser extracts CR context from ``$GITHUB_EVENT_PATH`` without assuming
one fixed lifecycle model. A separate planner layer accepts caller-supplied
stage and action mappings so product repos can implement their own workflow
state machines while keeping business logic in Python instead of YAML.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class GitHubEventContext:
    cr_id: str | None
    mode: str  # "new", "iterate", "cancel", "skip"
    pr_number: int | None = None
    reason: str = ""
    event_name: str = ""
    branch_ref: str = ""
    review_state: str = ""
    merged: bool = False
    labels: tuple[str, ...] = ()
    dispatch_stage: str = ""


@dataclass(frozen=True)
class GitHubLifecyclePlan:
    cr_id: str | None
    action: str
    stage: str = ""
    mode: str = "skip"
    pr_number: int | None = None
    reason: str = ""
    event_name: str = ""
    branch_ref: str = ""
    review_state: str = ""
    merged: bool = False


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
        head_ref = (
            (event.get("pull_request", {}) or {}).get("head", {}).get("ref", "")
            or (event.get("issue", {}) or {}).get("pull_request", {}).get("head", {}).get("ref", "")
        )
    if merged is None:
        merged = bool((event.get("pull_request", {}) or {}).get("merged", False))
    if merge_commit_sha is None:
        merge_commit_sha = str((event.get("pull_request", {}) or {}).get("merge_commit_sha", "") or "")
    raw_labels = (
        ((event.get("pull_request", {}) or {}).get("labels", []) or [])
        or ((event.get("issue", {}) or {}).get("labels", []) or [])
    )
    labels = tuple(
        lab.get("name", "")
        for lab in raw_labels
        if isinstance(lab, dict) and lab.get("name")
    )
    review_state = str((event.get("review", {}) or {}).get("state", "") or "")
    dispatch_stage = str((event.get("inputs", {}) or {}).get("stage", "") or "")

    # -- workflow_dispatch --------------------------------------------------
    if event_name == "workflow_dispatch" or manual_cr_id:
        cr_id = manual_cr_id or (event.get("inputs", {}) or {}).get("cr_id", "")
        if cr_id:
            return GitHubEventContext(
                cr_id=cr_id,
                mode="new",
                event_name=event_name or "workflow_dispatch",
                branch_ref=head_ref or "",
                merged=bool(merged),
                labels=labels,
                dispatch_stage=dispatch_stage,
            )
        return GitHubEventContext(
            cr_id=None,
            mode="skip",
            reason="No cr_id input",
            event_name=event_name or "workflow_dispatch",
            branch_ref=head_ref or "",
            merged=bool(merged),
            labels=labels,
            dispatch_stage=dispatch_stage,
        )

    # -- pull_request -------------------------------------------------------
    if event_name == "pull_request":
        if merged:
            # Merged PR: extract CR from branch name → new design/spec/impl
            cr_id = _extract_cr(head_ref)
            if not cr_id and merge_commit_sha:
                # Fallback: git diff the merge commit
                cr_id = _extract_cr_from_diff(merge_commit_sha)
            if cr_id:
                return GitHubEventContext(
                    cr_id=cr_id,
                    mode="new",
                    event_name=event_name,
                    branch_ref=head_ref or "",
                    merged=True,
                    labels=labels,
                )
            return GitHubEventContext(
                cr_id=None,
                mode="skip",
                reason="No CR ID in merged PR",
                event_name=event_name,
                branch_ref=head_ref or "",
                merged=True,
                labels=labels,
            )

        # Open or closed (not merged) PR
        if head_ref.startswith(("spec/", "design/", "feat/")):
            cr_id = _extract_cr(head_ref)
            if not merged:
                return GitHubEventContext(
                    cr_id=cr_id,
                    mode="cancel" if cr_id else "skip",
                    event_name=event_name,
                    branch_ref=head_ref or "",
                    merged=False,
                    labels=labels,
                )
            return GitHubEventContext(
                cr_id=cr_id,
                mode="new",
                event_name=event_name,
                branch_ref=head_ref or "",
                merged=True,
                labels=labels,
            )

        pr_number = (event.get("pull_request", {}) or {}).get("number")
        return GitHubEventContext(
            cr_id=_extract_cr(head_ref),
            mode="skip",
            pr_number=pr_number,
            reason="PR not merged and branch not spec/design/feat prefix",
            event_name=event_name,
            branch_ref=head_ref or "",
            merged=bool(merged),
            labels=labels,
        )

    # -- pull_request_review ------------------------------------------------
    if event_name == "pull_request_review":
        review = event.get("review", {}) or {}
        pr_info = event.get("pull_request", {}) or {}
        head_ref = pr_info.get("head", {}).get("ref", "")
        cr_id = _extract_cr(head_ref)
        if not cr_id:
            return GitHubEventContext(
                cr_id=None,
                mode="skip",
                reason="No CR ID in PR branch",
                event_name=event_name,
                branch_ref=head_ref or "",
                review_state=review_state,
                labels=labels,
            )
        if review.get("state") == "changes_requested":
            return GitHubEventContext(
                cr_id=cr_id, mode="iterate",
                pr_number=pr_info.get("number"),
                event_name=event_name,
                branch_ref=head_ref or "",
                review_state=review_state,
                labels=labels,
            )
        # Approved / commented reviews intentionally remain mode="skip" here.
        # The planner layer is responsible for mapping review_state to a
        # caller-defined action, so clients can choose whether "approved"
        # advances a stage, records status, or does nothing.
        return GitHubEventContext(
            cr_id=cr_id,
            mode="skip",
            reason="Review not changes_requested; planner may still map review_state",
            pr_number=pr_info.get("number"),
            event_name=event_name,
            branch_ref=head_ref or "",
            review_state=review_state,
            labels=labels,
        )

    # -- issue_comment ------------------------------------------------------
    if event_name == "issue_comment":
        issue = event.get("issue", {}) or {}
        if not issue.get("pull_request"):
            return GitHubEventContext(
                cr_id=None,
                mode="skip",
                reason="Issue comment is not on a pull request",
                event_name=event_name,
                branch_ref=head_ref or "",
                merged=bool(merged),
                labels=labels,
            )
        cr_id = _extract_cr(str(issue.get("title", "") or ""))
        if not cr_id:
            cr_id = _extract_cr(str((event.get("comment", {}) or {}).get("body", "") or ""))
        return GitHubEventContext(
            cr_id=cr_id,
            mode="skip",
            pr_number=issue.get("number"),
            reason="" if cr_id else "No CR ID in pull request comment context",
            event_name=event_name,
            branch_ref=head_ref or "",
            merged=bool(merged),
            labels=labels,
        )

    # -- repository_dispatch ------------------------------------------------
    if event_name == "repository_dispatch":
        cr_id = (event.get("client_payload", {}) or {}).get("cr_id", "")
        if cr_id:
            return GitHubEventContext(
                cr_id=cr_id,
                mode="new",
                event_name=event_name,
                branch_ref=head_ref or "",
                merged=bool(merged),
                labels=labels,
            )
        return GitHubEventContext(
            cr_id=None,
            mode="skip",
            reason="No cr_id in dispatch payload",
            event_name=event_name,
            branch_ref=head_ref or "",
            merged=bool(merged),
            labels=labels,
        )

    return GitHubEventContext(
        cr_id=None,
        mode="skip",
        reason=f"Unhandled event: {event_name}",
        event_name=event_name,
        branch_ref=head_ref or "",
        merged=bool(merged),
        labels=labels,
        review_state=review_state,
        dispatch_stage=dispatch_stage,
    )


def infer_stage(
    context: GitHubEventContext,
    *,
    branch_stage_pairs: Iterable[tuple[str, str]] = (),
    stage_label_prefix: str = "",
) -> str:
    """Infer stage from labels or branch prefixes.

    Label-based stage inference is optional and caller-controlled so product
    repos can opt into their own label scheme. When both a stage label and a
    branch prefix exist, the label wins.
    """
    if stage_label_prefix:
        for label in context.labels:
            if label.startswith(stage_label_prefix):
                return label[len(stage_label_prefix):]
    for prefix, stage in branch_stage_pairs:
        if context.branch_ref.startswith(prefix):
            return stage
    return ""


def plan_github_event(
    context: GitHubEventContext,
    *,
    branch_stage_pairs: Iterable[tuple[str, str]] = (),
    stage_label_prefix: str = "",
    dispatch_actions: dict[str, str] | None = None,
    review_actions: dict[str, str] | None = None,
    pr_actions: dict[str, str] | None = None,
    default_action: str = "",
    manual_stage: str = "",
) -> GitHubLifecyclePlan:
    """Apply caller-supplied lifecycle mappings to a parsed GitHub event.

    The planner is intentionally generic: action names are opaque strings
    defined by the caller, not by MedHarness. This keeps MedHarness testable
    while allowing product repos such as WebTPS to own their lifecycle model.
    """
    dispatch_actions = dispatch_actions or {}
    review_actions = review_actions or {}
    pr_actions = pr_actions or {}

    if not context.cr_id:
        return GitHubLifecyclePlan(
            cr_id=None,
            action=default_action or context.mode,
            mode=context.mode,
            pr_number=context.pr_number,
            reason=context.reason or "No CR context",
            event_name=context.event_name,
            branch_ref=context.branch_ref,
            review_state=context.review_state,
            merged=context.merged,
        )

    stage = manual_stage or context.dispatch_stage or infer_stage(
        context,
        branch_stage_pairs=branch_stage_pairs,
        stage_label_prefix=stage_label_prefix,
    )
    action = default_action or context.mode

    if context.event_name == "workflow_dispatch":
        action = dispatch_actions.get(stage, action)
    elif context.event_name == "pull_request_review":
        review_state = context.review_state.lower()
        action = review_actions.get(review_state, action)
        if stage:
            action = review_actions.get(f"{review_state}:{stage}", action)
    elif context.event_name == "pull_request":
        state_key = "merged" if context.merged else "closed"
        action = pr_actions.get(state_key, action)
        if stage:
            action = pr_actions.get(f"{state_key}:{stage}", action)
    elif context.event_name == "issue_comment":
        if stage:
            action = dispatch_actions.get(stage, action)
    elif context.event_name == "repository_dispatch":
        if stage:
            action = dispatch_actions.get(stage, action)

    return GitHubLifecyclePlan(
        cr_id=context.cr_id,
        action=action,
        stage=stage,
        mode=context.mode,
        pr_number=context.pr_number,
        reason=context.reason,
        event_name=context.event_name,
        branch_ref=context.branch_ref,
        review_state=context.review_state,
        merged=context.merged,
    )


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
