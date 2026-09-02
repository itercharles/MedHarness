"""Approval records as DHF items.

An approval is a regulated record: it says who accepted what, and against which
state of the design. Before this module that record lived in a GitHub label and
a ``docs/reviews/*.md`` file — outside the DHF, so absent from the traceability
matrix, from evidence bundles, and from every gate.

The revision an approval covers is deliberately *not* a field. It is the commit
that introduced the record. Writing it into the file would be circular — the SHA
of the commit containing ``APR-014`` cannot appear inside ``APR-014`` — and would
create a second source of truth that a hand edit can make disagree with git.
:func:`resolve_approval` derives it instead.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

VERDICTS = ("approved", "rejected", "needs_revision")
STAGES = ("design", "develop", "release")

_VERDICT_LINE = re.compile(r"^\s*\*\*Verdict:\*\*\s*(.+?)\s*$", re.MULTILINE)
# The workflow emits both kinds; a code review is a decision about the develop
# stage, not the design one, and importing it as "design" would misattribute it.
_REVIEW_FILENAME = re.compile(
    r"^(?P<cr>[A-Z]+-\d+)-(?P<kind>Design|Code)-Review\.md$"
)
_KIND_TO_STAGE = {"design": "design", "code": "develop"}


def record_approval(
    dhf_root: Path,
    *,
    approves: str,
    stage: str,
    verdict: str,
    approver: str,
    scope: str = "",
    notes: str = "",
    author: str = "system",
) -> dict:
    """Create an APR item for a decision.

    Raises:
        ValueError: If the verdict or stage is not one this workflow models, or
            the approver is empty — an approval nobody is accountable for is not
            a record worth writing.
    """
    import dhfkit.api as api

    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}; got {verdict!r}")
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {', '.join(STAGES)}; got {stage!r}")
    if not approver.strip():
        raise ValueError(
            "approver is required: an approval record must name who is accountable, "
            "which in CI is never the committing bot."
        )

    return api.create_item(
        dhf_root,
        {
            "type": "APR",
            "title": f"{verdict.replace('_', ' ').title()} — {approves} ({stage})",
            "approves": [approves],
            "stage": stage,
            "verdict": verdict,
            "approver": approver.strip(),
            "scope": scope,
            "notes": notes,
        },
        author=author,
        cr_id=approves if approves.startswith("CR-") else None,
    )


def find_approvals(dhf_root: Path, *, approves: str = "", stage: str = "") -> list[dict]:
    """Return APR items, optionally narrowed to an artifact and stage."""
    import dhfkit.api as api

    results = []
    for item in api.list_items(dhf_root):
        if not str(item.get("id", "")).startswith("APR-"):
            continue
        if approves and approves not in (item.get("approves") or []):
            continue
        if stage and item.get("stage") != stage:
            continue
        results.append(item)
    return sorted(results, key=lambda i: i["id"])


def resolve_approval(dhf_root: Path, apr_id: str) -> dict:
    """Resolve the commit an approval was made against.

    The introducing commit is the approved state: the record is written once, so
    the oldest commit touching its file is the moment of decision.

    Returns ``{"apr_id", "revision", "short_revision", "date", "committer",
    "message", "resolved"}``. ``resolved`` is False when the DHF is not a git
    repository or the record has not been committed yet — a real state for a
    record created moments ago, and one the caller should report rather than
    treat as an approval against nothing.
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_root)
    item = adapter.get_item(apr_id)
    if item is None:
        raise ValueError(f"Approval record '{apr_id}' not found.")

    unresolved = {
        "apr_id": apr_id,
        "revision": None,
        "short_revision": None,
        "date": None,
        "committer": None,
        "message": None,
        "resolved": False,
        "reason": "",
    }

    path = _item_path(dhf_root, apr_id)
    if path is None:
        return {**unresolved, "reason": f"No file on disk for {apr_id}."}

    repo = getattr(adapter, "_git", None) or _git_repo(dhf_root.resolve())
    if repo is None or not repo.is_available():
        return {**unresolved, "reason": "DHF is not a git repository."}

    history = repo.get_file_history(path, max_count=100)
    if not history:
        return {
            **unresolved,
            "reason": f"{apr_id} has no commit yet — the record is uncommitted.",
        }

    introducing = history[-1]
    return {
        "apr_id": apr_id,
        "revision": introducing["sha"],
        "short_revision": introducing.get("short_sha") or introducing["sha"][:8],
        "date": introducing["date"],
        "committer": introducing["author"],
        "message": introducing["message"],
        "resolved": True,
        "reason": "",
    }


def import_review_files(dhf_root: Path, reviews_dir: Path, *,
                        approver: str = "", author: str = "system") -> dict:
    """Backfill APR items from the legacy ``docs/reviews/*.md`` convention.

    Files whose CR already has a design-stage approval are skipped, so the
    command is safe to re-run.
    """
    if not reviews_dir.is_dir():
        return {"imported": [], "skipped": [], "errors": [
            f"No review directory at {reviews_dir}."
        ]}

    imported: list[dict] = []
    skipped: list[dict] = []
    errors: list[str] = []

    # Globbing "*-Review.md" made a naming mismatch invisible: a directory of
    # CR-013-Design.md files reported "0 imported, 0 skipped" with nothing in
    # errors, and `verify completion` then failed with "no approval record"
    # with no way to connect the two. Look at every .md and say what was passed
    # over, so a convention this does not read is reported rather than silent.
    for review in sorted(reviews_dir.glob("*.md")):
        match = _REVIEW_FILENAME.match(review.name)
        if not match:
            skipped.append({
                "file": review.name,
                "reason": "filename does not match <CR-ID>-Design-Review.md or "
                          "<CR-ID>-Code-Review.md",
            })
            continue
        cr_id = match.group("cr")
        stage = _KIND_TO_STAGE[match.group("kind").lower()]

        if find_approvals(dhf_root, approves=cr_id, stage=stage):
            skipped.append(
                {"file": review.name, "reason": f"{cr_id} already has a {stage} record"}
            )
            continue

        verdict = _verdict_from(review.read_text(encoding="utf-8"))
        if verdict is None:
            skipped.append({"file": review.name, "reason": "no **Verdict:** line"})
            continue

        try:
            item = record_approval(
                dhf_root,
                approves=cr_id, stage=stage, verdict=verdict,
                approver=approver or "imported@unknown",
                scope=f"Imported from {review.name}.",
                notes=(
                    "Backfilled from the legacy review-file convention. The "
                    "approved revision is this record's own commit, not the "
                    "review file's."
                ),
                author=author,
            )
        except Exception as exc:  # noqa: BLE001 — reported per file, not fatal
            errors.append(f"{review.name}: {exc}")
            continue
        imported.append({
            "file": review.name, "apr_id": item["id"],
            "verdict": verdict, "stage": stage,
        })

    return {"imported": imported, "skipped": skipped, "errors": errors}


def _verdict_from(text: str) -> Optional[str]:
    match = _VERDICT_LINE.search(text)
    if not match:
        return None
    raw = match.group(1).strip().lower()
    if "needs revision" in raw or "needs_revision" in raw:
        return "needs_revision"
    if "approved" in raw:
        return "approved"
    if "rejected" in raw:
        return "rejected"
    return None


def _item_path(dhf_root: Path, item_id: str) -> Optional[Path]:
    """Absolute path to an item's file.

    Resolved because git reports an absolute working directory, and --dhf is
    normally given relative; comparing the two unresolved makes every lookup
    fail with a subpath error.
    """
    for candidate in (dhf_root.resolve() / "items").rglob(f"{item_id}.yaml"):
        return candidate
    return None


def _git_repo(dhf_root: Path):
    from dhfkit.repository.git import GitRepository

    try:
        return GitRepository(dhf_root)
    except Exception:  # noqa: BLE001 — absence of git is a reported state
        return None
