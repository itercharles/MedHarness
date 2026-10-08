"""`verify completion` — a CR's record is complete and the items it changed are verified."""

from __future__ import annotations

from pathlib import Path

from medharness.services.envelope import envelope_from
from medharness.services.verify_tests import validate_verification_completeness


def _check_cr_fields(adapter, cr_item: dict | None, cr_id: str) -> list[dict]:
    """The CR's own record: what its type's lifecycle requires of the move to `completed`.

    `cr.yaml` says it, once, and `item transition ... completed` refuses on it; this asks the
    same question after the fact, in CI, where a hand-edited status cannot skip it.
    """
    if cr_item is None:
        return [{"field": "cr_item", "issue": f"CR {cr_id} is not in the DHF."}]
    return [
        {"field": c["field"],
         "issue": f"CR {cr_id} — {c['name']}: `{c['field']}` is not recorded."}
        for c in adapter.unmet_criteria(cr_id, "completed")
    ]


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
    1. The CR meets the criteria its type puts on the move to ``completed`` (cr.yaml).
    2. Every item in ``affected_items`` exists in the DHF.
    3. Those of a verifiable type have ``verification_method`` set.
    4. Those with ``Test`` have passing JUnit evidence. Without JUnit paths the
       evidence is not checked, and the result says so rather than passing
       quietly.

    Approval is not checked here. It lives in the pull request, and GitHub's
    branch protection enforces it.
    """
    from dhfkit.store import open_store

    adapter = open_store(dhf_path)
    cr_item = adapter.get_item(cr_id)
    incomplete_cr_fields = _check_cr_fields(adapter, cr_item, cr_id)
    cr_item = cr_item or {}

    verifiable_types = set(adapter.config.requirement_types())
    items_by_id = {it["id"]: it for it in adapter.list_items()}
    affected = [uid for uid in cr_item.get("affected_items") or [] if isinstance(uid, str)]
    missing_items = sorted(uid for uid in affected if uid not in items_by_id)
    verifiable = sorted({
        items_by_id[uid].get("type") for uid in affected
        if uid in items_by_id and items_by_id[uid].get("type") in verifiable_types
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
        gaps = verify_result.get("missing_method", [])
        unverified = verify_result.get("unverified_test", [])
        manual = verify_result.get("manual_review_required", [])
        if not verify_result["passed"]:
            verify_summary = verify_result["summary"]

    passed = not (incomplete_cr_fields or missing_items or gaps or unverified)

    parts: list[str] = []
    warnings: list[str] = []
    if verifiable and not junit_paths:
        # Test evidence cannot be enforced against nothing, so a Test-verified
        # item passes on the strength of no evidence. Say so.
        parts.append("test evidence not checked (no JUnit given)")
        warnings.append("test evidence not checked — pass --junit to check the Test-verified items")
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
        "warnings": warnings,
        "cr_id": cr_id,
        "incomplete_cr_fields": incomplete_cr_fields,
        "missing_items": missing_items,
        "verification_gaps": gaps,
        "unverified_test": unverified,
        "manual_review_required": manual,
        "summary": summary,
    })
