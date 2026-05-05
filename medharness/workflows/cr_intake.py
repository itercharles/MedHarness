"""Issue-to-CR intake helpers for reusable CR workflows."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dhfkit.change_requests import (
    ChangeRequestPreparation as CrPreparation,
    ExternalChangeRequest,
    build_change_request_data,
    next_change_request_id,
    prepare_change_request,
)


@dataclass(frozen=True)
class IssueContext:
    number: int
    title: str
    body: str
    state: str
    html_url: str
    author: str
    milestone: str | None


def load_github_issue_event(path: Path) -> IssueContext:
    payload = json.loads(path.read_text(encoding="utf-8"))
    issue = payload.get("issue") or {}
    user = issue.get("user") or {}
    milestone = issue.get("milestone") or {}
    return IssueContext(
        number=int(issue["number"]),
        title=str(issue.get("title") or "").strip(),
        body=str(issue.get("body") or "").strip(),
        state=str(issue.get("state") or ""),
        html_url=str(issue.get("html_url") or ""),
        author=str(user.get("login") or "unknown"),
        milestone=str(milestone.get("title") or "").strip() or None,
    )


def load_comments(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def issue_has_cr_marker(comments: list[dict[str, Any]], marker_name: str) -> str | None:
    marker_re = re.compile(rf"<!--\s*{re.escape(marker_name)}:\s*(CR-\d+)\s*-->")
    for comment in comments:
        match = marker_re.search(str(comment.get("body") or ""))
        if match:
            return match.group(1)
    return None


def next_cr_id(items: list[dict[str, Any]]) -> str:
    return next_change_request_id(items)


def find_existing_cr_for_issue(items: list[dict[str, Any]], source_issue_url: str) -> str | None:
    from dhfkit.change_requests import find_change_request_by_source

    return find_change_request_by_source(items, source_issue_url)


def current_iso_week_milestone(today: dt.date | None = None) -> str:
    current = today or dt.date.today()
    iso_year, iso_week, _ = current.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def extract_issue_form_field(body: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"^###\s+{re.escape(heading)}\s*$\n(?P<value>.*?)(?=^###\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return None
    value = match.group("value").strip()
    return value or None


def issue_to_external_change_request(issue: IssueContext) -> ExternalChangeRequest:
    requested_change = extract_issue_form_field(issue.body, "Requested change") or issue.body
    acceptance_criteria = extract_issue_form_field(issue.body, "Acceptance criteria") or ""
    justification = extract_issue_form_field(issue.body, "User value / justification") or (
        "Maintainer assigned this issue to the active release milestone, "
        "indicating it is accepted for CR intake."
    )
    category = extract_issue_form_field(issue.body, "Change category") or "Feature"
    return ExternalChangeRequest(
        title=issue.title,
        description=requested_change,
        justification=justification,
        requested_by=issue.author,
        source_url=issue.html_url,
        target_version=issue.milestone or "",
        category=category,
        priority="Medium",
        content=acceptance_criteria,
        source_number=issue.number,
    )


def build_cr_data(issue: IssueContext) -> dict[str, Any]:
    return build_change_request_data(issue_to_external_change_request(issue))


def prepare_cr_from_issue(
    issue: IssueContext,
    active_milestone: str,
    comments: list[dict[str, Any]],
    *,
    write: bool,
    adapter,
    marker_name: str = "medharness-cr",
    branch_prefix: str = "cr",
    title_prefix: str = "cr",
) -> CrPreparation:
    if not active_milestone:
        return CrPreparation(False, "CR intake milestone is not configured.")
    if issue.state != "open":
        return CrPreparation(False, f"Issue is {issue.state}, not open.")
    if issue.milestone != active_milestone:
        return CrPreparation(
            False,
            f"Issue milestone {issue.milestone!r} is not active milestone {active_milestone!r}.",
        )

    marker_cr = issue_has_cr_marker(comments, marker_name)
    return prepare_change_request(
        issue_to_external_change_request(issue),
        adapter,
        write=write,
        known_cr_id=marker_cr,
        branch_prefix=branch_prefix,
        title_prefix=title_prefix,
        source_label="issue",
    )
