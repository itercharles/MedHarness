"""Parse and plan GitHub event payloads for CI workflows.

Reading the payload (``read_event``) is kept apart from interpreting it
(``parse_github_event``, ``plan_github_event``), so the interpretation is a
function of a dict and can be tested without files, environment variables or
git. The planner accepts caller-supplied stage and action mappings so product
repos can implement their own workflow state machines while keeping business
logic in Python instead of YAML.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping


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
    issue_number: int | None = None


@dataclass(frozen=True)
class GitHubLifecyclePlan:
    stage: str
    action: str


_CR_RE = re.compile(r"CR-\d+")

#: GitHub links a PR to an issue only through a closing keyword. A bare "#12" is
#: a reference, not a link, so matching it would name an issue the PR does not
#: close.
#:
#: Keyword form only: an issue linked through the GitHub UI leaves no trace in
#: the payload, so an absent `issue_number` means "not derivable", not "none".
_CLOSES_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#(\d+)",
    re.IGNORECASE,
)


def _linked_issue(body: str) -> int | None:
    """The issue a pull-request body says it closes, or None."""
    match = _CLOSES_RE.search(body or "")
    return int(match.group(1)) if match else None


def read_event(
    event_path: Path | None = None,
    environ: Mapping[str, str] = os.environ,
) -> tuple[dict, str]:
    """The event payload and its name, as GitHub Actions hands them to a step.

    *event_path* defaults to ``$GITHUB_EVENT_PATH``; the name is always
    ``$GITHUB_EVENT_NAME``. An absent payload is ``{}`` — a manual run has none.
    """
    raw_path = environ.get("GITHUB_EVENT_PATH", "")
    # is_file(), not exists(): an unset variable becomes Path("") -> Path("."),
    # and a directory would pass exists() and then raise on read.
    event_path = event_path or (Path(raw_path) if raw_path else None)
    event: dict = {}
    if event_path is not None and event_path.is_file():
        try:
            event = json.loads(event_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Raise: swallowing this yields `{}`, which parses to the same
            # cr_id=None/skip/exit-0 a genuine no-op event produces.
            raise ValueError(
                f"GitHub event payload at {event_path} could not be read: {exc}"
            ) from exc
    return event, environ.get("GITHUB_EVENT_NAME", "")


def merge_commit_files(sha: str) -> str:
    """Names of the files a merge commit changed, one per line; "" if git fails."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{sha}~1", sha],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def parse_github_event(
    event: dict,
    event_name: str,
    *,
    manual_cr_id: str = "",
    changed_files: Callable[[str], str] = merge_commit_files,
) -> GitHubEventContext:
    """Which CR a GitHub event concerns, and this tool's own reading of it.

    *changed_files* is consulted only for a merged PR whose branch names no CR:
    it maps the merge commit's SHA to the files that commit changed.
    """
    pr = event.get("pull_request") or {}
    issue = event.get("issue") or {}
    if event_name == "workflow_dispatch" or manual_cr_id:
        event_name = event_name or "workflow_dispatch"
    head_ref = (
        (pr.get("head") or {}).get("ref", "")
        or ((issue.get("pull_request") or {}).get("head") or {}).get("ref", "")
        or ""
    )
    cr_id, mode, pr_number, reason = _classify(
        event, event_name, head_ref, manual_cr_id, changed_files,
    )
    return GitHubEventContext(
        cr_id=cr_id,
        mode=mode,
        pr_number=pr_number,
        reason=reason,
        event_name=event_name,
        branch_ref=head_ref,
        review_state=str((event.get("review") or {}).get("state", "") or ""),
        merged=bool(pr.get("merged", False)),
        labels=tuple(
            lab.get("name", "")
            for lab in (pr.get("labels") or issue.get("labels") or [])
            if isinstance(lab, dict) and lab.get("name")
        ),
        dispatch_stage=str((event.get("inputs") or {}).get("stage", "") or ""),
        # For issue_comment on a PR, GitHub puts the PR body under "issue".
        issue_number=_linked_issue(
            str(pr.get("body", "") or "") or str(issue.get("body", "") or "")
        ),
    )


def _classify(
    event: dict,
    event_name: str,
    head_ref: str,
    manual_cr_id: str,
    changed_files: Callable[[str], str],
) -> tuple[str | None, str, int | None, str]:
    """``(cr_id, mode, pr_number, reason)`` for one event."""
    pr = event.get("pull_request") or {}

    if event_name == "workflow_dispatch" or manual_cr_id:
        cr_id = manual_cr_id or (event.get("inputs") or {}).get("cr_id", "")
        return (cr_id, "new", None, "") if cr_id else (None, "skip", None, "No cr_id input")

    if event_name == "pull_request":
        if pr.get("merged"):
            cr_id = _extract_cr(head_ref)
            sha = str(pr.get("merge_commit_sha", "") or "")
            if not cr_id and sha:
                cr_id = _extract_cr(changed_files(sha))
            return (cr_id, "new", None, "") if cr_id else (None, "skip", None, "No CR ID in merged PR")
        if head_ref.startswith(("spec/", "design/", "feat/")):
            cr_id = _extract_cr(head_ref)
            return cr_id, "cancel" if cr_id else "skip", None, ""
        return (_extract_cr(head_ref), "skip", pr.get("number"),
                "PR not merged and branch not spec/design/feat prefix")

    if event_name == "pull_request_review":
        cr_id = _extract_cr(head_ref)
        if not cr_id:
            return None, "skip", None, "No CR ID in PR branch"
        if (event.get("review") or {}).get("state") == "changes_requested":
            return cr_id, "iterate", pr.get("number"), ""
        # Approved / commented reviews stay "skip": the planner maps
        # review_state to a caller-defined action.
        return (cr_id, "skip", pr.get("number"),
                "Review not changes_requested; planner may still map review_state")

    if event_name == "issue_comment":
        issue = event.get("issue") or {}
        if not issue.get("pull_request"):
            return None, "skip", None, "Issue comment is not on a pull request"
        cr_id = (_extract_cr(str(issue.get("title", "") or ""))
                 or _extract_cr(str((event.get("comment") or {}).get("body", "") or "")))
        return (cr_id, "skip", issue.get("number"),
                "" if cr_id else "No CR ID in pull request comment context")

    if event_name == "repository_dispatch":
        cr_id = (event.get("client_payload") or {}).get("cr_id", "")
        return (cr_id, "new", None, "") if cr_id else (None, "skip", None, "No cr_id in dispatch payload")

    return None, "skip", None, f"Unhandled event: {event_name}"


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
    action = default_action or context.mode

    if not context.cr_id:
        return GitHubLifecyclePlan(stage="", action=action)

    stage = manual_stage or context.dispatch_stage or infer_stage(
        context,
        branch_stage_pairs=branch_stage_pairs,
        stage_label_prefix=stage_label_prefix,
    )

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
    elif context.event_name in ("issue_comment", "repository_dispatch"):
        if stage:
            action = dispatch_actions.get(stage, action)

    return GitHubLifecyclePlan(stage=stage, action=action)


def _extract_cr(text: str) -> str | None:
    m = _CR_RE.search(text or "")
    return m.group(0) if m else None
