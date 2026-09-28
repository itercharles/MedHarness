"""`verify completion` — a CR's record is complete and the items it changed are verified."""

from __future__ import annotations

from pathlib import Path

from medharness.services.envelope import envelope_from
from medharness.services.verify_tests import validate_verification_completeness


# Item types that carry a verification_method field — RISK, RCM, SWDD, etc. do not.
_VERIFIABLE_ITEM_TYPES = frozenset({"CRS", "SRS", "SYS", "SOUP"})


def _check_cr_fields(cr_item: dict, cr_id: str) -> list[dict]:
    """Check that the CR fields `build plan` records are populated.

    Returns a list of issue dicts for each missing or invalid field.
    """
    issues: list[dict] = []
    if not str(cr_item.get("implementation_notes") or "").strip():
        issues.append({
            "field": "implementation_notes",
            "issue": (
                f"CR {cr_id} — implementation_notes is absent; "
                "`build plan` records the implementation plan."
            ),
        })
    if not isinstance(cr_item.get("affected_risk_items"), list):
        issues.append({
            "field": "affected_risk_items",
            "issue": (
                f"CR {cr_id} — affected_risk_items is absent; "
                "`build plan` records the risk impact ([] if none)."
            ),
        })
    if not isinstance(cr_item.get("affected_items"), list):
        issues.append({
            "field": "affected_items",
            "issue": (
                f"CR {cr_id} — affected_items is absent; "
                "`build plan` records the items it changed ([] if none)."
            ),
        })
    triage = cr_item.get("triage_result")
    if not isinstance(triage, dict) or triage.get("verdict") != "approved":
        issues.append({
            "field": "triage_result",
            "issue": (
                f"CR {cr_id} — triage_result.verdict is not 'approved'; "
                "`build plan` records the triage decision."
            ),
        })
    return issues


def _closure_errors(incomplete=(), missing=(), gaps=(), unverified=()) -> list[str]:
    """Phrase closure findings for the envelope."""
    return (
        [i["issue"] for i in incomplete]
        + [f"{m}: in affected_items but absent from the DHF" for m in missing]
        + [f"{g['id']}: no verification_method declared" for g in gaps]
        + [f"{g['id']}: declares Test but has no passing JUnit evidence" for g in unverified]
    )


def cr_closure_gate(
    cr_id: str,
    dhf_path: Path,
    junit_paths: tuple[Path, ...] = (),
) -> dict:
    """Verify that a CR is closed: its record complete, its items present and verified.

    Checks:
    1. The CR carries implementation_notes, affected_risk_items, affected_items
       and an approved triage_result.
    2. Every item in ``affected_items`` exists in the DHF.
    3. Those of a verifiable type have ``verification_method`` set.
    4. Those with ``Test`` have passing JUnit evidence. Without JUnit paths the
       evidence is not checked, and the result says so rather than passing
       quietly.

    Approval is not checked here. It lives in the pull request, and GitHub's
    branch protection enforces it.
    """
    from dhfkit.local_adapter import LocalDHFAdapter

    adapter = LocalDHFAdapter(dhf_path)
    cr_item = adapter.get_item(cr_id) or {}
    incomplete_cr_fields = _check_cr_fields(cr_item, cr_id)

    items_by_id = {it["id"]: it for it in adapter.list_items()}
    affected = [uid for uid in cr_item.get("affected_items") or [] if isinstance(uid, str)]
    missing_items = sorted(uid for uid in affected if uid not in items_by_id)
    verifiable = sorted({
        items_by_id[uid].get("type") for uid in affected
        if uid in items_by_id and items_by_id[uid].get("type") in _VERIFIABLE_ITEM_TYPES
    })

    gaps: list = []
    unverified: list = []
    manual: list = []
    verify_summary = ""
    if verifiable:
        # Only the items this CR touched. Scanning the whole DHF charged one CR
        # with every starter and legacy requirement that never declared a method.
        verify_result = validate_verification_completeness(
            dhf_path,
            junit_paths=junit_paths,
            req_types=tuple(verifiable),
            enforce_test_evidence=True,
            item_ids=set(affected),
        )
        gaps = verify_result["details"].get("missing_method", [])
        unverified = verify_result["details"].get("unverified_test", [])
        manual = verify_result["details"].get("manual_review_required", [])
        if not verify_result["passed"]:
            verify_summary = verify_result["summary"]

    passed = not (incomplete_cr_fields or missing_items or gaps or unverified)

    parts: list[str] = []
    if verifiable and not junit_paths:
        # Test evidence cannot be enforced against nothing, so a Test-verified
        # item passes on the strength of no evidence. Say so.
        parts.append("test evidence not checked (no JUnit given)")
    if incomplete_cr_fields:
        parts.append(f"{len(incomplete_cr_fields)} CR field(s) incomplete")
    if missing_items:
        parts.append(f"{len(missing_items)} affected item(s) not in the DHF")
    if verify_summary:
        parts.append(verify_summary)
    if not passed:
        summary = f"CR {cr_id} is not closed: " + ", ".join(parts)
    else:
        summary = (f"CR {cr_id} closure verified — {len(affected)} affected item(s) present"
                   + (f"; {parts[0]}." if parts else " and verified."))

    return envelope_from("verify completion", {
        "passed": passed,
        "errors": _closure_errors(incomplete=incomplete_cr_fields, missing=missing_items,
                                  gaps=gaps, unverified=unverified),
        "cr_id": cr_id,
        "incomplete_cr_fields": incomplete_cr_fields,
        "missing_items": missing_items,
        "verification_gaps": gaps,
        "unverified_test": unverified,
        "manual_review_required": manual,
        "summary": summary,
    })
