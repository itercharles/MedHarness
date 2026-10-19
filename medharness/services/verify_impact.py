"""`verify impact`: whether a CR's record of its impact holds for the branch that carries it.

`build plan` writes `impact_analysis`, `reviewed_items` and `affected_risk_items` onto the CR and checks them
before it finishes; this runs the same judgement on whatever is on the machine, so an agent that wrote them
itself, or a person, finds out before CI does.
"""

from __future__ import annotations

from pathlib import Path

from dhfkit.store import open_store
from medharness.services import design_validation, git
from medharness.services.envelope import envelope_from


def _failed(cr_id: str, since_ref: str, summary: str, field: str, issue: str, fix: str) -> dict:
    return envelope_from("verify impact", {
        "cr_id": cr_id, "since_ref": since_ref, "passed": False, "summary": summary,
        "errors": [f"{field}: {issue}"], "findings": [{"field": field, "issue": issue, "fix": fix}],
    })


def verify_impact(repo_root: Path, dhf_path: Path, cr_id: str, *, since_ref: str | None = None) -> dict:
    since_ref = git.resolve_since_ref(repo_root, since_ref)
    store = open_store(dhf_path)
    if not store.tracks_files:
        return envelope_from("verify impact", {
            "cr_id": cr_id, "since_ref": since_ref, "passed": False,
            "summary": f"{cr_id}: the items are not files in Git, so there is no diff to check.",
            "errors": [git.FILES_IN_GIT.format(command="verify impact", store=store.store_type)],
        })
    if store.get_item(cr_id) is None:
        return _failed(cr_id, since_ref, f"{cr_id}: not in the DHF.", "cr_item",
                       f"CR item '{cr_id}' is not in the DHF.", f"Create {cr_id}, or name the CR the branch is for.")
    try:
        changed = git.collect_dhf_item_changes(repo_root, since_ref, dhf_path)
    except git.DiffUnavailable as exc:
        return _failed(
            cr_id, since_ref, f"{cr_id}: could not read the diff against {since_ref}.", "diff_unavailable",
            f"Could not diff against {since_ref}: {exc}.",
            f"Fetch it (`git fetch origin main`), or pass --since-ref with a ref that exists here. "
            f"A shallow clone or a repo with no remote has no {since_ref}.",
        )

    findings = design_validation.impact_findings(dhf_path, cr_id, changed)
    warnings = [
        *design_validation.check_verification_quality(dhf_path, changed),
        *design_validation.check_near_duplicates(dhf_path, changed),
        *design_validation.check_large_edits(repo_root, since_ref, dhf_path, cr_id),
        *design_validation.check_test_points_follow_requirements(repo_root, dhf_path, since_ref),
    ]
    return envelope_from("verify impact", {
        "cr_id": cr_id,
        "since_ref": since_ref,
        "passed": not findings,
        "summary": f"{cr_id}: {len(findings)} finding(s) in its impact record since {since_ref}.",
        "errors": [f"{f['field']}: {f['issue']}" for f in findings],
        "warnings": [f"{w['code']}: {w['message']}" for w in warnings],
        "findings": findings,
    })
